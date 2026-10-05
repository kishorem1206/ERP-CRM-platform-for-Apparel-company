"""Lead Intelligence: normalization, duplicate/repeat-contact detection, and
the deterministic scoring engine (Phase 1 of the Lead Intelligence spec).

Core principle from the spec, Step 23: scoring is deterministic and backend-
controlled, never delegated to an LLM. Every signal below is a plain rule
over real fields; nothing here calls out to an AI model.

Layout:
  1. Normalization (phone/email, adapter interface)
  2. Duplicate detection
  3. Repeat-contact detection
  4. Signal extraction
  5. Scoring engine (score_lead)
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.crm import (
    CrmLead, CrmLeadProduct, CrmLeadScoringRule, CrmLeadServiceArea,
    CrmLeadSource, CrmLeadStageHistory, CrmOrganization, CrmPerson,
)
from app.models.sales import Customer
from app.models.user import User

SCORING_VERSION = 1

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "hotmail.com", "outlook.com",
    "rediffmail.com", "icloud.com", "live.com", "aol.com", "protonmail.com",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
QUANTITY_RE = re.compile(r"\b\d[\d,]*\s*(pcs?|pieces?|units?|kgs?|dozen|boxes)\b", re.IGNORECASE)


# ── 1. Normalization ────────────────────────────────────────────────────────

def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Returns a 10-digit canonical Indian mobile number, or None if the
    input has no plausible phone number in it. Strips +91/91/0 prefixes."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def normalize_email(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    email = raw.strip().lower()
    return email if EMAIL_RE.match(email) else None


def is_business_email(email: Optional[str]) -> bool:
    """True only for a validly-shaped email on a non-free-provider domain.
    Never claims disposable/fake - we have no reliable provider list for
    that, per spec Step 10's explicit caution."""
    norm = normalize_email(email)
    if not norm:
        return False
    domain = norm.rsplit("@", 1)[-1]
    return domain not in FREE_EMAIL_DOMAINS


@dataclass
class NormalizedLeadInput:
    """The common shape every LeadSourceAdapter produces (spec Step 2/3),
    regardless of where the lead came from. `raw` is kept verbatim so a
    broken integration can always be debugged from what was actually sent."""
    source_name: str
    title: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    enquiry_message: Optional[str] = None
    quantity: Optional[str] = None
    product_interest: Optional[str] = None
    source_lead_id: Optional[str] = None
    received_at: Optional[datetime] = None
    raw: dict[str, Any] = field(default_factory=dict)


def normalize_manual_lead(*, title: str, description: Optional[str] = None) -> NormalizedLeadInput:
    """Adapter for leads entered by hand through the existing New Lead form.
    Every lead created today already goes through this path implicitly;
    this function makes that explicit and gives manual entry the same
    normalized shape every other source will produce."""
    return NormalizedLeadInput(
        source_name="Manual", title=title, enquiry_message=description,
        received_at=datetime.now(timezone.utc), raw={"title": title, "description": description},
    )


def normalize_indiamart_payload(payload: dict[str, Any]) -> NormalizedLeadInput:
    """IndiaMART adapter. No IndiaMART credentials exist in this deployment
    (confirmed in docs/LEAD_INTELLIGENCE_AUDIT.md - zero prior integration),
    so this is built and must be tested against fixture payloads only. Field
    names below follow IndiaMART's commonly documented lead-push shape;
    they are NOT verified against a live account and must be checked
    against real payloads before this adapter is connected to a real
    webhook."""
    sender = payload.get("SENDER", {}) if isinstance(payload.get("SENDER"), dict) else {}
    query = payload.get("QUERY", {}) if isinstance(payload.get("QUERY"), dict) else {}
    return NormalizedLeadInput(
        source_name="IndiaMART",
        title=query.get("QUERY_PRODUCT_NAME") or query.get("QUERY_MESSAGE", "")[:200] or "IndiaMART enquiry",
        name=sender.get("SENDER_NAME"),
        phone=sender.get("SENDER_MOBILE") or sender.get("SENDER_PHONE"),
        email=sender.get("SENDER_EMAIL"),
        company_name=sender.get("SENDER_COMPANY"),
        city=sender.get("SENDER_CITY"),
        enquiry_message=query.get("QUERY_MESSAGE"),
        quantity=query.get("QUERY_QUANTITY"),
        product_interest=query.get("QUERY_PRODUCT_NAME"),
        source_lead_id=str(payload.get("UNIQUE_QUERY_ID") or ""),
        received_at=datetime.now(timezone.utc),
        raw=payload,
    )


# ── 2. Duplicate detection ──────────────────────────────────────────────────

@dataclass
class DuplicateMatch:
    status: str  # "exact" | "high_confidence" | "possible" | "none"
    matched_person_id: Optional[UUID] = None
    matched_organization_id: Optional[UUID] = None
    matched_customer_id: Optional[UUID] = None
    reason: str = ""


async def find_duplicate(
    db: AsyncSession, company_id: UUID, *, phone: Optional[str] = None,
    email: Optional[str] = None, organization_name: Optional[str] = None,
    exclude_person_id: Optional[UUID] = None,
) -> DuplicateMatch:
    """Classifies a prospective new lead's contact details against existing
    CrmPerson / Customer records. Never auto-merges - spec Step 12 is
    explicit that uncertain matches must stay "possible" for a human to
    review, not be silently combined.

    `exclude_person_id` matters when scoring a lead that is *already*
    linked to a person: without it, that person's own phone/email always
    matches themselves, so every linked lead would show as an "exact"
    duplicate of itself. Pass it when checking a lead that has a person
    already attached; omit it for a pre-save check on fresh form input."""
    phone_n = normalize_phone(phone)
    email_n = normalize_email(email)

    persons = (await db.execute(
        select(CrmPerson).where(CrmPerson.company_id == company_id, CrmPerson.id != exclude_person_id)
        if exclude_person_id else
        select(CrmPerson).where(CrmPerson.company_id == company_id)
    )).scalars().all()

    phone_match: Optional[CrmPerson] = None
    email_match: Optional[CrmPerson] = None
    for p in persons:
        if phone_n and any(normalize_phone(n.get("value")) == phone_n for n in (p.contact_numbers or [])):
            phone_match = p
        if email_n and any(normalize_email(e.get("value")) == email_n for e in (p.emails or [])):
            email_match = p

    if phone_match and email_match and phone_match.id == email_match.id:
        return DuplicateMatch("exact", matched_person_id=phone_match.id, reason="Phone and email both match an existing contact")
    if phone_match:
        return DuplicateMatch("high_confidence", matched_person_id=phone_match.id, reason="Phone number matches an existing contact")
    if email_match:
        return DuplicateMatch("possible", matched_person_id=email_match.id, reason="Email matches an existing contact")

    customer_match = None
    if phone_n or email_n:
        customers = (await db.execute(select(Customer).where(Customer.company_id == company_id))).scalars().all()
        for c in customers:
            if phone_n and normalize_phone(c.mobile or c.whatsapp_no) == phone_n:
                customer_match = c
                break
            if email_n and normalize_email(c.email) == email_n:
                customer_match = c
                break
    if customer_match:
        return DuplicateMatch("high_confidence", matched_customer_id=customer_match.id, reason="Contact details match an existing customer account")

    if organization_name:
        org_match = (await db.execute(
            select(CrmOrganization).where(
                CrmOrganization.company_id == company_id,
                CrmOrganization.name.ilike(organization_name.strip()),
            ).limit(1)
        )).scalar_one_or_none()
        if org_match:
            return DuplicateMatch("possible", matched_organization_id=org_match.id, reason="Company name matches an existing organization")

    return DuplicateMatch("none")


# ── 3. Repeat-contact detection ─────────────────────────────────────────────

@dataclass
class RepeatContactInfo:
    previous_lead_id: UUID
    previous_date: datetime
    previous_source: Optional[str]
    previous_status: str
    previous_stage_name: Optional[str]
    previous_assigned_to_name: Optional[str]


async def find_repeat_contact(
    db: AsyncSession, company_id: UUID, *, exclude_lead_id: Optional[UUID],
    person_id: Optional[UUID], organization_id: Optional[UUID],
) -> Optional[RepeatContactInfo]:
    """Has this person/organization enquired before? Checked against
    CrmLead directly (not just the duplicate-match person), since a repeat
    contact may already be correctly linked to the same CrmPerson without
    being a "duplicate" of this new lead at all - it's the same person
    returning, which is the point."""
    if not person_id and not organization_id:
        return None
    filters = [CrmLead.company_id == company_id]
    if exclude_lead_id:
        filters.append(CrmLead.id != exclude_lead_id)
    if person_id and organization_id:
        from sqlalchemy import or_
        filters.append(or_(CrmLead.person_id == person_id, CrmLead.organization_id == organization_id))
    elif person_id:
        filters.append(CrmLead.person_id == person_id)
    else:
        filters.append(CrmLead.organization_id == organization_id)

    prev = (await db.execute(
        select(CrmLead).where(*filters).order_by(CrmLead.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if not prev:
        return None

    source_name = None
    if prev.source_id:
        src = (await db.execute(select(CrmLeadSource.name).where(CrmLeadSource.id == prev.source_id))).scalar_one_or_none()
        source_name = src

    stage_name = None
    last_stage = (await db.execute(
        select(CrmLeadStageHistory.to_stage_name)
        .where(CrmLeadStageHistory.lead_id == prev.id)
        .order_by(CrmLeadStageHistory.changed_at.desc()).limit(1)
    )).scalar_one_or_none()
    stage_name = last_stage

    assigned_name = None
    if prev.assigned_to:
        assigned_name = (await db.execute(select(User.full_name).where(User.id == prev.assigned_to))).scalar_one_or_none()

    return RepeatContactInfo(
        previous_lead_id=prev.id, previous_date=prev.created_at, previous_source=source_name,
        previous_status=prev.status, previous_stage_name=stage_name, previous_assigned_to_name=assigned_name,
    )


async def get_location_tier(db: AsyncSession, company_id: UUID, city: Optional[str]) -> Optional[str]:
    """Shared by scoring (location.* signals) and assignment (location_tier
    rule condition) - one place that knows how a city resolves to a
    configured service-area tier, so the two can never disagree."""
    if not city:
        return None
    return (await db.execute(
        select(CrmLeadServiceArea.tier).where(
            CrmLeadServiceArea.company_id == company_id,
            CrmLeadServiceArea.location_name.ilike(city.strip()),
        ).limit(1)
    )).scalar_one_or_none()


# ── 4 & 5. Signal extraction + scoring engine ───────────────────────────────

async def score_lead(db: AsyncSession, lead: CrmLead) -> None:
    """Computes and sets score/priority/breakdown/duplicate/repeat-contact
    fields directly on `lead`. Does not commit - the caller's existing
    transaction does that. Safe to call multiple times (re-scoring); each
    call fully recomputes rather than incrementally adjusting."""
    company_id = lead.company_id

    person = (await db.execute(select(CrmPerson).where(CrmPerson.id == lead.person_id))).scalar_one_or_none() if lead.person_id else None
    organization = (await db.execute(select(CrmOrganization).where(CrmOrganization.id == lead.organization_id))).scalar_one_or_none() if lead.organization_id else None
    customer = (await db.execute(select(Customer).where(Customer.id == lead.customer_id))).scalar_one_or_none() if lead.customer_id else None
    lead_products = (await db.execute(select(CrmLeadProduct).where(CrmLeadProduct.lead_id == lead.id))).scalars().all()

    phone = (person.contact_numbers[0]["value"] if person and person.contact_numbers else None)
    email = (person.emails[0]["value"] if person and person.emails else None)
    city = (person.city if person and person.city else None)

    # Duplicate + repeat-contact detection run as part of scoring, since
    # "repeat.previous_enquiry" is itself a scoring signal.
    dup = await find_duplicate(
        db, company_id, phone=phone, email=email,
        organization_name=organization.name if organization else None,
        exclude_person_id=lead.person_id,
    )
    lead.duplicate_status = dup.status
    lead.duplicate_of_lead_id = None  # CrmLead isn't the match target here (person/org/customer are) - nothing to set today

    repeat = await find_repeat_contact(
        db, company_id, exclude_lead_id=lead.id, person_id=lead.person_id, organization_id=lead.organization_id,
    )
    lead.is_repeat_contact = repeat is not None

    description = (lead.description or "").strip()
    has_quantity = bool(lead_products) or bool(QUANTITY_RE.search(description))
    has_product = bool(lead_products)
    is_detailed_requirement = len(description) >= 60 and (has_quantity or has_product)
    valid_phone = normalize_phone(phone) is not None
    valid_email = normalize_email(email) is not None
    business_email = is_business_email(email)
    company_identified = organization is not None
    gst_available = bool(customer and customer.gstin)

    service_area_tier = await get_location_tier(db, company_id, city)

    lower_desc = description.lower()
    signals: dict[str, bool] = {
        "requirement.quantity_specified": has_quantity,
        "requirement.product_specified": has_product,
        "requirement.detailed": is_detailed_requirement,
        "intent.direct_enquiry": bool(person and person.contact_numbers),
        "intent.quotation_request": any(k in lower_desc for k in ("quotation", "quote", "price")),
        "intent.sample_request": "sample" in lower_desc,
        "intent.catalogue_request": any(k in lower_desc for k in ("catalogue", "catalog")),
        "contact.valid_phone": valid_phone,
        "contact.missing_phone": phone is None,
        "contact.valid_email": valid_email,
        "contact.business_email": business_email,
        "business.company_identified": company_identified,
        "business.gst_available": gst_available,
        "location.preferred": service_area_tier == "preferred",
        "location.secondary": service_area_tier == "secondary",
        "location.non_serviceable": service_area_tier == "non_serviceable",
        "repeat.previous_enquiry": lead.is_repeat_contact,
        "quality.detailed_message": len(description) >= 120,
        "quality.vague_message": len(description) < 15,
    }

    rules = (await db.execute(
        select(CrmLeadScoringRule).where(CrmLeadScoringRule.company_id == company_id, CrmLeadScoringRule.is_active.is_(True))
    )).scalars().all()

    breakdown: list[dict[str, Any]] = []
    total = 0
    for rule in rules:
        if signals.get(rule.code):
            total += rule.weight
            breakdown.append({"category": rule.category, "code": rule.code, "label": rule.label, "points": rule.weight})

    score = max(0, min(100, total))

    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    high_t = company.lead_score_high_threshold if company else 80
    med_t = company.lead_score_medium_threshold if company else 50
    priority = "high" if score >= high_t else ("medium" if score >= med_t else "low")

    lead.score = score
    lead.priority = priority
    lead.score_version = SCORING_VERSION
    lead.score_breakdown = breakdown
    lead.scored_at = datetime.now(timezone.utc)
