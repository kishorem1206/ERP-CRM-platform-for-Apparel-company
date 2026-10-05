import base64
import csv
import io
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

import aiosmtplib
from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy import and_, delete, func, insert, literal_column, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.v1.deps import AuthUser, DBSession
from app.models.company import Company
from app.models.crm import (
    CrmActivity, CrmEmail, CrmEmailTemplate, CrmFollowUpType, CrmLead, CrmLeadAssignmentHistory, CrmLeadImport,
    CrmLeadSource, CrmLeadStageHistory, CrmLeadTag, CrmLeadType,
    CrmNote, CrmOrganization, CrmPerson, CrmPipeline, CrmPipelineStage, CrmProduct,
    CrmAdSpend, CrmLeadProduct, CrmQuote, CrmQuoteItem, CrmSmtpConfig, CrmTag, CrmTask,
    CrmLeadScoringRule, CrmLeadServiceArea,
    CrmLeadAssignmentRule, CrmLeadAssignmentPool,
)
from app.services.lead_intelligence import (
    find_duplicate, find_repeat_contact, score_lead,
)
from app.services.lead_assignment import auto_assign_lead, response_target_for_priority
from app.services.crm_kpi import (
    OPEN_AGE_DAYS, CohortFilter, OpenPipelineFilter, compare, created_in_period, load_cohort,
    lead_quality_breakdown, load_open_pipeline, previous_period, qualified_clause, summarize,
)
from app.models.master import Product, ProductVariant
from app.models.sales import Customer
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.crm import (
    ActivityCreate, ActivityDoneUpdate, ActivityOut, ActivityUpdate,
    AssignableUserOut,
    CrmReportParams,
    EmailCreate, EmailListOut, EmailOut,
    EmailTemplateCreate, EmailTemplateOut, EmailTemplateUpdate,
    FollowUpTypeOut,
    LeadAssignIn, LeadAssignmentHistoryOut, LeadBulkActionIn,
    LeadConvertIn, LeadCreate, LeadImportOut, LeadKanbanStageOut, LeadListOut, LeadOut,
    LeadSourceCreate, LeadSourceOut, LeadSourceUpdate,
    LeadStageUpdate, LeadStatusUpdate, LeadTypeOut, LeadUpdate,
    NoteCreate, NoteOut, NoteUpdate,
    OrganizationCreate, OrganizationListOut, OrganizationOut, OrganizationUpdate,
    Person360Out, LeadForPerson360,
    PersonCreate, PersonListOut, PersonOut, PersonUpdate,
    PipelineOut, QualificationStageUpdate,
    ProductCreate, ProductOut, ProductUpdate,
    QuoteCreate, QuoteItemOut, QuoteListOut, QuoteOut, QuoteStatusUpdate, QuoteUpdate,
    SmtpConfigCreate, SmtpConfigOut,
    ScoringRuleOut, ScoringRuleUpdate, ScoringThresholdsOut, ScoringThresholdsUpdate,
    ServiceAreaCreate, ServiceAreaOut, ServiceAreaUpdate,
    DuplicateCheckOut, RepeatContactOut,
    AssignmentRuleCreate, AssignmentRuleUpdate, AssignmentRuleOut,
    AssignmentPoolMemberIn, AssignmentPoolMemberOut,
    ResponseTargetsOut, ResponseTargetsUpdate,
    PredictiveScoringReadinessOut,
    StageHistoryOut,
    TagCreate, TagOut,
    AdSpendCreate, AdSpendOut, AdSpendUpdate,
    LeadProductCreate, LeadProductOut,
    TaskCompleteIn, TaskCreate, TaskOut, TaskUpdate,
)
from app.services.notification import create_notification, publish_notification

logger = logging.getLogger(__name__)


# NOTE: password_encrypted uses base64 for obfuscation only.
# Production should use AES-256 or a secrets manager (e.g. AWS Secrets Manager).
def _enc(p: str) -> str:
    return base64.b64encode(p.encode()).decode()


def _dec(p: str) -> str:
    return base64.b64decode(p.encode()).decode()

router = APIRouter(prefix="/crm", tags=["crm"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _conflict(exc: IntegrityError, on_duplicate: str, on_reference: str) -> HTTPException:
    detail = str(exc.orig) if exc.orig else str(exc)
    if "unique" in detail.lower() or "duplicate" in detail.lower():
        return HTTPException(409, on_duplicate)
    return HTTPException(409, on_reference)


_LEAD_OPTS = [
    selectinload(CrmLead.stage),
    selectinload(CrmLead.person),
    selectinload(CrmLead.organization),
    selectinload(CrmLead.tags),
]


def _person_phone(person) -> str | None:
    if not person:
        return None
    nums = person.contact_numbers or []
    return nums[0]["value"] if nums else None


def _person_email(person) -> str | None:
    if not person:
        return None
    emails = person.emails or []
    return emails[0]["value"] if emails else None


def _time_to_minutes(a: datetime | None, b: datetime | None) -> int | None:
    """Minutes from a to b, or None if either is missing or b precedes a."""
    if not a or not b or b < a:
        return None
    return int((b - a).total_seconds() // 60)


def _lead_out(lead: CrmLead, name_map: dict[UUID, str] | None = None) -> LeadOut:
    name_map = name_map or {}
    return LeadOut(
        id=lead.id, company_id=lead.company_id, title=lead.title,
        description=lead.description, lead_value=lead.lead_value,
        temperature=lead.temperature,
        status=lead.status, lost_reason=lead.lost_reason,
        expected_close_date=lead.expected_close_date, closed_at=lead.closed_at,
        pipeline_id=lead.pipeline_id, stage_id=lead.stage_id,
        stage_name=lead.stage.name if lead.stage else None,
        stage_color=lead.stage.color if lead.stage else None,
        source_id=lead.source_id, type_id=lead.type_id,
        person_id=lead.person_id,
        person_name=lead.person.name if lead.person else None,
        person_phone=_person_phone(lead.person),
        person_email=_person_email(lead.person),
        organization_id=lead.organization_id,
        organization_name=lead.organization.name if lead.organization else None,
        customer_id=lead.customer_id, assigned_to=lead.assigned_to,
        assigned_to_name=name_map.get(lead.assigned_to),
        assigned_date=lead.assigned_date,
        assigned_by=lead.assigned_by,
        assigned_by_name=name_map.get(lead.assigned_by),
        assignment_status=lead.assignment_status,
        next_follow_up_at=lead.next_follow_up_at,
        follow_up_type=lead.follow_up_type,
        follow_up_reason=lead.follow_up_reason,
        follow_up_notes=lead.follow_up_notes,
        follow_up_status=lead.follow_up_status,
        last_contacted_at=lead.last_contacted_at,
        contact_outcome=lead.contact_outcome,
        next_action=lead.next_action,
        created_by=lead.created_by, created_at=lead.created_at, updated_at=lead.updated_at,
        tags=[TagOut.model_validate(t) for t in (lead.tags or [])],
        score=lead.score, priority=lead.priority, score_version=lead.score_version,
        score_breakdown=lead.score_breakdown, scored_at=lead.scored_at,
        duplicate_status=lead.duplicate_status, is_repeat_contact=lead.is_repeat_contact,
        first_contacted_at=lead.first_contacted_at, response_target_at=lead.response_target_at,
        time_to_assignment_minutes=_time_to_minutes(lead.created_at, lead.assigned_date),
        time_to_first_response_minutes=_time_to_minutes(lead.created_at, lead.first_contacted_at),
        sales_order_id=lead.sales_order_id,
    )


def _lead_list_out(lead: CrmLead, name_map: dict[UUID, str] | None = None) -> LeadListOut:
    name_map = name_map or {}
    return LeadListOut(
        id=lead.id, title=lead.title, lead_value=lead.lead_value,
        temperature=lead.temperature, status=lead.status,
        stage_id=lead.stage_id,
        stage_name=lead.stage.name if lead.stage else None,
        stage_color=lead.stage.color if lead.stage else None,
        person_id=lead.person_id,
        person_name=lead.person.name if lead.person else None,
        person_phone=_person_phone(lead.person),
        person_email=_person_email(lead.person),
        organization_id=lead.organization_id,
        organization_name=lead.organization.name if lead.organization else None,
        assigned_to=lead.assigned_to,
        assigned_to_name=name_map.get(lead.assigned_to),
        assignment_status=lead.assignment_status,
        next_follow_up_at=lead.next_follow_up_at,
        follow_up_type=lead.follow_up_type,
        follow_up_status=lead.follow_up_status,
        created_at=lead.created_at,
        score=lead.score, priority=lead.priority,
        duplicate_status=lead.duplicate_status, is_repeat_contact=lead.is_repeat_contact,
        first_contacted_at=lead.first_contacted_at, response_target_at=lead.response_target_at,
        sales_order_id=lead.sales_order_id,
    )


async def _resolve_user_names(db, company_id: UUID, ids: set[UUID | None]) -> dict[UUID, str]:
    """Batch-resolve user ids to display names, avoiding N+1 lookups."""
    clean_ids = {i for i in ids if i}
    if not clean_ids:
        return {}
    result = await db.execute(
        select(User.id, User.full_name).where(User.id.in_(clean_ids), User.company_id == company_id)
    )
    return {uid: name for uid, name in result.all()}


async def _sync_lead_followup_fields(db, lead_id: UUID) -> None:
    """Recomputes a lead's forward-looking follow-up fields from its
    activity timeline — the single place these fields are derived, so they
    can never drift from the activities that actually back them. Call after
    any activity create/update/delete/done-toggle that touches a lead_id.
    Does not commit."""
    result = await db.execute(
        select(CrmLead).where(CrmLead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        return

    next_result = await db.execute(
        select(CrmActivity)
        .where(
            CrmActivity.lead_id == lead_id,
            CrmActivity.is_done.is_(False),
            CrmActivity.schedule_from.is_not(None),
        )
        .order_by(CrmActivity.schedule_from.asc())
        .limit(1)
    )
    next_activity = next_result.scalar_one_or_none()

    if next_activity:
        lead.next_follow_up_at = next_activity.schedule_from
        lead.follow_up_type = next_activity.type
        lead.follow_up_reason = next_activity.comment
        lead.follow_up_status = "scheduled"
    else:
        lead.next_follow_up_at = None
        lead.follow_up_type = None
        lead.follow_up_reason = None
        if lead.follow_up_status == "scheduled":
            # Nothing left scheduled — only demote, never invent a
            # "completed" state for a lead that was never followed up on.
            lead.follow_up_status = "completed"


async def _assign_lead(
    db, lead: CrmLead, new_assignee_id: UUID | None, by_user_id: UUID, by_user_name: str | None,
    note: str | None = None, task_due_at: datetime | None = None,
) -> None:
    """Shared assignment logic for the dedicated assign endpoint and bulk-action
    assign — stamps assigned_by/assigned_date/assignment_status, writes an
    audit history row, and notifies the new assignee. Does not commit."""
    old_assignee_id = lead.assigned_to
    name_map = await _resolve_user_names(db, lead.company_id, {old_assignee_id, new_assignee_id})

    lead.assigned_to = new_assignee_id
    lead.assigned_by = by_user_id
    lead.assigned_date = _now()
    lead.assignment_status = "assigned" if new_assignee_id else "unassigned"
    lead.updated_at = _now()

    db.add(CrmLeadAssignmentHistory(
        lead_id=lead.id,
        from_assignee_id=old_assignee_id,
        to_assignee_id=new_assignee_id,
        from_assignee_name=name_map.get(old_assignee_id),
        to_assignee_name=name_map.get(new_assignee_id),
        changed_by=by_user_id,
        changed_by_name=by_user_name,
        note=note,
        changed_at=_now(),
    ))

    if new_assignee_id and new_assignee_id != old_assignee_id:
        notif = await create_notification(
            db,
            company_id=lead.company_id,
            notification_type="lead_assigned",
            title="New lead assigned",
            body=f"{lead.title} has been assigned to you.",
            user_id=new_assignee_id,
            data={"lead_id": str(lead.id)},
        )
        try:
            publish_notification(str(lead.company_id), {
                "id": str(notif.id), "type": "lead_assigned",
                "title": notif.title, "body": notif.body, "user_id": str(new_assignee_id),
            })
        except Exception:
            logger.warning("Failed to publish lead_assigned notification to Redis", exc_info=True)

        db.add(CrmTask(
            company_id=lead.company_id,
            title=f"Make first contact: {lead.title}",
            lead_id=lead.id,
            assigned_to=new_assignee_id,
            # Priority-aware when a response target is known (auto-assignment,
            # spec Step 3) - otherwise the same 24h default as before.
            due_at=task_due_at or (_now() + timedelta(hours=24)),
            priority="high" if lead.priority == "high" else "medium",
            source="lead_assignment",
            created_by=by_user_id,
            created_at=_now(), updated_at=_now(),
        ))

        try:
            from app.services.whatsapp_automation import fire_event, resolve_company_name, resolve_customer_name

            context = {
                "customer_name": await resolve_customer_name(db, lead),
                "company_name": await resolve_company_name(db, lead.company_id),
                "employee_name": name_map.get(new_assignee_id) or "",
                "lead_title": lead.title,
            }
            await fire_event(db, lead.company_id, "lead_assigned", context, lead=lead)
        except Exception:
            logger.warning("Failed to fire lead_assigned WhatsApp automation", exc_info=True)


async def _get_lead(lead_id: UUID, company_id: UUID, db) -> CrmLead:
    result = await db.execute(
        select(CrmLead).options(*_LEAD_OPTS)
        .where(CrmLead.id == lead_id, CrmLead.company_id == company_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


# ── Organizations ─────────────────────────────────────────────────────────────

@router.get("/organizations")
async def list_organizations(db: DBSession, user: AuthUser, search: str | None = None):
    user.require("crm.view")
    q = select(CrmOrganization).where(CrmOrganization.company_id == user.company_id)
    if search:
        q = q.where(CrmOrganization.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(CrmOrganization.name))
    return ApiResponse(success=True, data=[OrganizationListOut.model_validate(o) for o in result.scalars().all()])


@router.post("/organizations", status_code=201)
async def create_organization(body: OrganizationCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    org = CrmOrganization(
        company_id=user.company_id, name=body.name, website=body.website,
        address=body.address, assigned_to=body.assigned_to,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return ApiResponse(success=True, data=OrganizationOut.model_validate(org), message="Organization created")


@router.get("/organizations/{org_id}")
async def get_organization(org_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmOrganization).where(CrmOrganization.id == org_id, CrmOrganization.company_id == user.company_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    return ApiResponse(success=True, data=OrganizationOut.model_validate(org))


@router.patch("/organizations/{org_id}")
async def update_organization(org_id: UUID, body: OrganizationUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmOrganization).where(CrmOrganization.id == org_id, CrmOrganization.company_id == user.company_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(org, field, val)
    org.updated_at = _now()
    await db.commit()
    await db.refresh(org)
    return ApiResponse(success=True, data=OrganizationOut.model_validate(org))


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(
        select(CrmOrganization).where(CrmOrganization.id == org_id, CrmOrganization.company_id == user.company_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    await db.delete(org)
    await db.commit()
    return ApiResponse(success=True, message="Organization deleted")


# ── Persons ───────────────────────────────────────────────────────────────────

@router.get("/persons")
async def list_persons(db: DBSession, user: AuthUser, search: str | None = None):
    user.require("crm.view")
    q = (
        select(CrmPerson, CrmOrganization.name)
        .outerjoin(CrmOrganization, CrmOrganization.id == CrmPerson.organization_id)
        .where(CrmPerson.company_id == user.company_id)
    )
    if search:
        q = q.where(CrmPerson.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(CrmPerson.name))
    data = []
    for person, org_name in result.all():
        out = PersonListOut.model_validate(person)
        out.org_name = org_name
        out.phone_numbers = person.contact_numbers
        data.append(out)
    return ApiResponse(success=True, data=data)


@router.post("/persons", status_code=201)
async def create_person(body: PersonCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    person = CrmPerson(
        company_id=user.company_id, name=body.name, job_title=body.job_title,
        emails=[e.model_dump() for e in body.emails],
        contact_numbers=[c.model_dump() for c in body.contact_numbers],
        whatsapp_number=body.whatsapp_number,
        organization_id=body.organization_id, customer_id=body.customer_id,
        assigned_to=body.assigned_to, created_by=user.user_id,
        created_at=now, updated_at=now,
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return ApiResponse(success=True, data=PersonOut.model_validate(person), message="Person created")


@router.get("/persons/{person_id}")
async def get_person(person_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmPerson).where(CrmPerson.id == person_id, CrmPerson.company_id == user.company_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    return ApiResponse(success=True, data=PersonOut.model_validate(person))


@router.patch("/persons/{person_id}")
async def update_person(person_id: UUID, body: PersonUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmPerson).where(CrmPerson.id == person_id, CrmPerson.company_id == user.company_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(person, field, val)
    person.updated_at = _now()
    await db.commit()
    await db.refresh(person)
    return ApiResponse(success=True, data=PersonOut.model_validate(person))


@router.delete("/persons/{person_id}")
async def delete_person(person_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(
        select(CrmPerson).where(CrmPerson.id == person_id, CrmPerson.company_id == user.company_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    await db.delete(person)
    await db.commit()
    return ApiResponse(success=True, message="Person deleted")


@router.get("/persons/{person_id}/360")
async def get_person_360(person_id: UUID, db: DBSession, user: AuthUser):
    """Contact 360 — person + all leads (by pipeline with stage strip) + activities + notes."""
    user.require("crm.view")
    result = await db.execute(
        select(CrmPerson)
        .options(selectinload(CrmPerson.organization))
        .where(CrmPerson.id == person_id, CrmPerson.company_id == user.company_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")

    # All leads for this person with pipeline+stage loaded
    leads_result = await db.execute(
        select(CrmLead)
        .options(
            selectinload(CrmLead.pipeline).selectinload(CrmPipeline.stages),
            selectinload(CrmLead.stage),
            selectinload(CrmLead.tags),
        )
        .where(CrmLead.person_id == person_id, CrmLead.company_id == user.company_id)
        .order_by(CrmLead.created_at.desc())
    )
    leads = leads_result.scalars().all()

    # Activities for this person
    activities_result = await db.execute(
        select(CrmActivity)
        .where(CrmActivity.person_id == person_id, CrmActivity.company_id == user.company_id)
        .order_by(CrmActivity.schedule_from.desc())
        .limit(50)
    )
    activities = activities_result.scalars().all()

    # Notes for this person
    notes_result = await db.execute(
        select(CrmNote)
        .where(CrmNote.person_id == person_id, CrmNote.company_id == user.company_id)
        .order_by(CrmNote.created_at.desc())
    )
    notes = notes_result.scalars().all()

    leads_out = []
    for lead in leads:
        all_stages = [
            {"id": str(s.id), "name": s.name, "color": s.color, "sort_order": s.sort_order,
             "is_won": s.is_won, "is_lost": s.is_lost}
            for s in (lead.pipeline.stages if lead.pipeline else [])
        ]
        leads_out.append(LeadForPerson360(
            id=lead.id, title=lead.title, lead_value=lead.lead_value,
            temperature=lead.temperature, status=lead.status,
            pipeline_id=lead.pipeline_id,
            pipeline_name=lead.pipeline.name if lead.pipeline else None,
            stage_id=lead.stage_id,
            stage_name=lead.stage.name if lead.stage else None,
            stage_color=lead.stage.color if lead.stage else None,
            all_stages=all_stages,
            assigned_to=lead.assigned_to, created_at=lead.created_at,
        ))

    return ApiResponse(success=True, data=Person360Out(
        id=person.id, name=person.name, job_title=person.job_title, city=person.city,
        emails=person.emails or [], contact_numbers=person.contact_numbers or [],
        whatsapp_number=person.whatsapp_number,
        organization_id=person.organization_id,
        organization_name=person.organization.name if person.organization else None,
        assigned_to=person.assigned_to, created_at=person.created_at,
        leads=leads_out,
        activities=[ActivityOut.model_validate(a) for a in activities],
        notes=[NoteOut.model_validate(n) for n in notes],
    ))


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/notes", status_code=201)
async def create_note(body: NoteCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    note = CrmNote(
        company_id=user.company_id,
        body=body.body,
        person_id=body.person_id,
        lead_id=body.lead_id,
        organization_id=body.organization_id,
        created_by=user.user_id,
        created_by_name=getattr(user, "full_name", None),
        created_at=now, updated_at=now,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return ApiResponse(success=True, data=NoteOut.model_validate(note), message="Note added")


@router.get("/notes")
async def list_notes(
    db: DBSession, user: AuthUser,
    person_id: UUID | None = None,
    lead_id: UUID | None = None,
    organization_id: UUID | None = None,
):
    user.require("crm.view")
    filters = [CrmNote.company_id == user.company_id]
    if person_id:
        filters.append(CrmNote.person_id == person_id)
    if lead_id:
        filters.append(CrmNote.lead_id == lead_id)
    if organization_id:
        filters.append(CrmNote.organization_id == organization_id)
    result = await db.execute(
        select(CrmNote).where(*filters).order_by(CrmNote.created_at.desc())
    )
    return ApiResponse(success=True, data=[NoteOut.model_validate(n) for n in result.scalars().all()])


@router.patch("/notes/{note_id}")
async def update_note(note_id: UUID, body: NoteUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmNote).where(CrmNote.id == note_id, CrmNote.company_id == user.company_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    note.body = body.body
    note.updated_at = _now()
    await db.commit()
    await db.refresh(note)
    return ApiResponse(success=True, data=NoteOut.model_validate(note))


@router.delete("/notes/{note_id}")
async def delete_note(note_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmNote).where(CrmNote.id == note_id, CrmNote.company_id == user.company_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    await db.delete(note)
    await db.commit()
    return ApiResponse(success=True, message="Note deleted")


# ── Pipelines ─────────────────────────────────────────────────────────────────

@router.get("/pipelines")
async def list_pipelines(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmPipeline)
        .options(selectinload(CrmPipeline.stages))
        .where(CrmPipeline.company_id == user.company_id)
        .order_by(CrmPipeline.name)
    )
    return ApiResponse(success=True, data=[PipelineOut.model_validate(p) for p in result.scalars().all()])


@router.put("/pipelines/{pipeline_id}/qualification-stage")
async def set_qualification_stage(pipeline_id: UUID, body: QualificationStageUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    result = await db.execute(
        select(CrmPipeline)
        .options(selectinload(CrmPipeline.stages))
        .where(CrmPipeline.id == pipeline_id, CrmPipeline.company_id == user.company_id)
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise HTTPException(404, "Pipeline not found")
    if body.stage_id is not None and not any(s.id == body.stage_id for s in pipeline.stages):
        raise HTTPException(400, "Stage does not belong to this pipeline")
    pipeline.qualified_stage_id = body.stage_id
    pipeline.updated_at = _now()
    await db.commit()
    refreshed = await db.execute(
        select(CrmPipeline).options(selectinload(CrmPipeline.stages)).where(CrmPipeline.id == pipeline_id)
    )
    return ApiResponse(success=True, data=PipelineOut.model_validate(refreshed.scalar_one()))


# ── Lead Sources / Types ──────────────────────────────────────────────────────

@router.get("/lead-sources")
async def list_lead_sources(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadSource).where(CrmLeadSource.company_id == user.company_id).order_by(CrmLeadSource.name)
    )
    return ApiResponse(success=True, data=[LeadSourceOut.model_validate(s) for s in result.scalars().all()])


@router.post("/lead-sources", status_code=201)
async def create_lead_source(body: LeadSourceCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Source name is required")
    source = CrmLeadSource(company_id=user.company_id, name=name, created_at=_now())
    db.add(source)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A source with this name already exists", "Cannot create source")
    await db.refresh(source)
    return ApiResponse(success=True, data=LeadSourceOut.model_validate(source), message="Source created")


@router.patch("/lead-sources/{source_id}")
async def update_lead_source(source_id: UUID, body: LeadSourceUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmLeadSource).where(CrmLeadSource.id == source_id, CrmLeadSource.company_id == user.company_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(404, "Source not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Source name is required")
        source.name = name
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A source with this name already exists", "Cannot update source")
    await db.refresh(source)
    return ApiResponse(success=True, data=LeadSourceOut.model_validate(source), message="Source updated")


@router.delete("/lead-sources/{source_id}")
async def delete_lead_source(source_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(
        select(CrmLeadSource).where(CrmLeadSource.id == source_id, CrmLeadSource.company_id == user.company_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(404, "Source not found")
    # crm_leads.source_id is ON DELETE SET NULL, so the IntegrityError path
    # Category relies on would never fire here — guard explicitly so a
    # delete can't silently orphan historical leads and corrupt past
    # reports' platform attribution.
    in_use = await db.execute(
        select(func.count(CrmLead.id)).where(CrmLead.source_id == source_id)
    )
    count = in_use.scalar() or 0
    if count > 0:
        raise HTTPException(409, f"Cannot delete — {count} lead(s) still use this source")
    await db.delete(source)
    await db.commit()
    return ApiResponse(success=True, message="Source deleted")


@router.get("/lead-types")
async def list_lead_types(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadType).where(CrmLeadType.company_id == user.company_id).order_by(CrmLeadType.name)
    )
    return ApiResponse(success=True, data=[LeadTypeOut.model_validate(t) for t in result.scalars().all()])


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.get("/tags")
async def list_tags(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmTag).where(CrmTag.company_id == user.company_id).order_by(CrmTag.name)
    )
    return ApiResponse(success=True, data=[TagOut.model_validate(t) for t in result.scalars().all()])


@router.post("/tags", status_code=201)
async def create_tag(body: TagCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    tag = CrmTag(
        company_id=user.company_id, name=body.name, color=body.color, created_at=_now(),
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return ApiResponse(success=True, data=TagOut.model_validate(tag), message="Tag created")


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmTag).where(CrmTag.id == tag_id, CrmTag.company_id == user.company_id)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "Tag not found")
    await db.delete(tag)
    await db.commit()


# ── Leads ─────────────────────────────────────────────────────────────────────

@router.get("/leads/check-duplicate")
async def check_lead_duplicate(
    db: DBSession, user: AuthUser,
    phone: str | None = None, email: str | None = None, organization_name: str | None = None,
):
    """Pre-save duplicate check (spec Step 12) - lets the New Lead form warn
    before a lead is created, not just after."""
    user.require("crm.view")
    match = await find_duplicate(db, user.company_id, phone=phone, email=email, organization_name=organization_name)
    return ApiResponse(success=True, data=DuplicateCheckOut(
        status=match.status, matched_person_id=match.matched_person_id,
        matched_organization_id=match.matched_organization_id,
        matched_customer_id=match.matched_customer_id, reason=match.reason,
    ))


@router.get("/leads/kanban")
async def leads_kanban(db: DBSession, user: AuthUser, pipeline_id: UUID | None = None):
    user.require("crm.view")
    pipeline_q = (
        select(CrmPipeline)
        .options(selectinload(CrmPipeline.stages))
        .where(CrmPipeline.company_id == user.company_id)
    )
    if pipeline_id:
        pipeline_q = pipeline_q.where(CrmPipeline.id == pipeline_id)
    else:
        pipeline_q = pipeline_q.where(
            CrmPipeline.is_default.is_(True), CrmPipeline.stages.any()
        ).order_by(CrmPipeline.created_at, CrmPipeline.id)
    pipeline_result = await db.execute(pipeline_q.limit(1))
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        return ApiResponse(success=True, data=[])

    leads_result = await db.execute(
        select(CrmLead)
        .options(*_LEAD_OPTS)
        .where(
            CrmLead.company_id == user.company_id,
            CrmLead.pipeline_id == pipeline.id,
            CrmLead.status == "open",
        )
    )
    leads = leads_result.scalars().all()

    stage_leads: dict[UUID, list[LeadListOut]] = {s.id: [] for s in pipeline.stages}
    for lead in leads:
        if lead.stage_id in stage_leads:
            stage_leads[lead.stage_id].append(_lead_list_out(lead))

    kanban = [
        LeadKanbanStageOut(
            stage_id=s.id, stage_name=s.name, stage_color=s.color,
            sort_order=s.sort_order, is_won=s.is_won, is_lost=s.is_lost,
            column_value=sum(
                (Decimal(str(lead.lead_value or 0)) for lead in stage_leads.get(s.id, [])),
                Decimal("0"),
            ),
            leads=stage_leads.get(s.id, []),
        )
        for s in pipeline.stages
    ]
    return ApiResponse(success=True, data=kanban)


@router.get("/leads")
async def list_leads(
    db: DBSession, user: AuthUser,
    stage_id: UUID | None = None, status: str | None = None,
    assigned_to: UUID | None = None, follow_up_due: bool = False,
    priority: str | None = None, search: str | None = None,
    pipeline_id: UUID | None = None, source_id: UUID | None = None,
    kpi: str | None = None, created_from: date | None = None, created_to: date | None = None,
    utc_offset_minutes: int = 0,
    page: int = 1, page_size: int = 50,
):
    user.require("crm.view")
    filters = [CrmLead.company_id == user.company_id]
    if created_from and created_to:
        filters.extend(created_in_period(user.company_id, created_from, created_to, utc_offset_minutes))
    if pipeline_id:
        filters.append(CrmLead.pipeline_id == pipeline_id)
    if source_id:
        filters.append(CrmLead.source_id == source_id)
    # Same definitions as GET /crm/reports/sales-kpis (services/crm_kpi.py).
    if kpi == "qualified":
        filters.append(qualified_clause())
    elif kpi == "won":
        filters.append(CrmLead.status == "won")
    elif kpi in ("open", "aged"):
        filters.extend([
            CrmLead.status == "open",
            CrmLead.stage_id.in_(select(CrmPipelineStage.id).where(
                CrmPipelineStage.is_won.is_(False), CrmPipelineStage.is_lost.is_(False)
            )),
            qualified_clause(),
        ])
        if kpi == "aged":
            filters.append(CrmLead.created_at < _now() - timedelta(days=OPEN_AGE_DAYS))
    elif kpi not in (None, "", "new"):
        raise HTTPException(400, "kpi must be new, qualified, won, open or aged")
    if stage_id:
        filters.append(CrmLead.stage_id == stage_id)
    if status:
        filters.append(CrmLead.status == status)
    if assigned_to:
        filters.append(CrmLead.assigned_to == assigned_to)
    if follow_up_due:
        filters.append(CrmLead.follow_up_status == "scheduled")
        filters.append(CrmLead.next_follow_up_at <= _now())
    if priority == "unscored":
        filters.append(CrmLead.priority.is_(None))
    elif priority:
        filters.append(CrmLead.priority == priority)
    if search:
        # The frontend has sent this param since the search box was built;
        # the backend never read it, so the box silently filtered nothing.
        # Found during the Lead Intelligence audit, fixed here alongside
        # the new priority filter it sits next to.
        filters.append(CrmLead.title.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count(CrmLead.id)).where(*filters))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CrmLead)
        .options(*_LEAD_OPTS)
        .where(*filters)
        .order_by(CrmLead.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    leads = result.scalars().all()
    name_map = await _resolve_user_names(db, user.company_id, {lead.assigned_to for lead in leads})
    return ApiResponse(
        success=True,
        data=[_lead_list_out(lead, name_map) for lead in leads],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/leads", status_code=201)
async def create_lead(body: LeadCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    lead = CrmLead(
        company_id=user.company_id, title=body.title, description=body.description,
        lead_value=body.lead_value, temperature=body.temperature, status="open",
        expected_close_date=body.expected_close_date,
        pipeline_id=body.pipeline_id, stage_id=body.stage_id,
        source_id=body.source_id, type_id=body.type_id,
        person_id=body.person_id, organization_id=body.organization_id,
        customer_id=body.customer_id, assigned_to=body.assigned_to,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(lead)
    await db.flush()
    await score_lead(db, lead)

    # Smart assignment (Phase 2, spec Steps 1-3): only when nobody picked an
    # assignee by hand. Auto-assignment reuses _assign_lead so notification,
    # the first-contact task, and the WhatsApp trigger all happen exactly
    # the same way a manual assignment would.
    if not body.assigned_to:
        company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
        candidate = await auto_assign_lead(db, lead)
        if candidate:
            target_at = response_target_for_priority(lead.priority, company) if company else None
            lead.response_target_at = target_at
            await _assign_lead(
                db, lead, candidate, by_user_id=user.user_id, by_user_name=None,
                note="Auto-assigned", task_due_at=target_at,
            )

    await db.commit()
    lead = await _get_lead(lead.id, user.company_id, db)
    name_map = await _resolve_user_names(db, user.company_id, {lead.assigned_to})
    return ApiResponse(success=True, data=_lead_out(lead, name_map), message="Lead created")


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    lead = await _get_lead(lead_id, user.company_id, db)
    name_map = await _resolve_user_names(db, user.company_id, {lead.assigned_to, lead.assigned_by})
    return ApiResponse(success=True, data=_lead_out(lead, name_map))


@router.patch("/leads/{lead_id}")
async def update_lead(lead_id: UUID, body: LeadUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    lead = await _get_lead(lead_id, user.company_id, db)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, val)
    lead.updated_at = _now()
    await db.commit()
    lead = await _get_lead(lead_id, user.company_id, db)
    return ApiResponse(success=True, data=_lead_out(lead))


@router.post("/leads/{lead_id}/rescore")
async def rescore_lead(lead_id: UUID, db: DBSession, user: AuthUser):
    """Manually recompute a lead's score - e.g. after editing its
    description or linking a person/organization. Scoring does not re-run
    automatically on every edit, so this is the explicit trigger."""
    user.require("crm.edit")
    lead = await _get_lead(lead_id, user.company_id, db)
    await score_lead(db, lead)
    await db.commit()
    lead = await _get_lead(lead_id, user.company_id, db)
    return ApiResponse(success=True, data=_lead_out(lead), message="Lead re-scored")


@router.get("/leads/{lead_id}/repeat-contact")
async def get_lead_repeat_contact(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    lead = await _get_lead(lead_id, user.company_id, db)
    repeat = await find_repeat_contact(
        db, user.company_id, exclude_lead_id=lead.id, person_id=lead.person_id, organization_id=lead.organization_id,
    )
    if not repeat:
        return ApiResponse(success=True, data=None)
    return ApiResponse(success=True, data=RepeatContactOut(
        previous_lead_id=repeat.previous_lead_id, previous_date=repeat.previous_date,
        previous_source=repeat.previous_source, previous_status=repeat.previous_status,
        previous_stage_name=repeat.previous_stage_name, previous_assigned_to_name=repeat.previous_assigned_to_name,
    ))


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    lead = await _get_lead(lead_id, user.company_id, db)
    await db.delete(lead)
    await db.commit()
    return ApiResponse(success=True, message="Lead deleted")


@router.patch("/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: UUID, body: LeadStageUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    lead = await _get_lead(lead_id, user.company_id, db)

    # Capture old stage name before changing
    old_stage_id = lead.stage_id
    old_stage_name = lead.stage.name if lead.stage else None

    # Resolve new stage name
    new_stage_name: str | None = None
    if body.stage_id:
        stage_result = await db.execute(select(CrmPipelineStage).where(CrmPipelineStage.id == body.stage_id))
        new_stage = stage_result.scalar_one_or_none()
        new_stage_name = new_stage.name if new_stage else None

    lead.stage_id = body.stage_id
    if body.pipeline_id:
        lead.pipeline_id = body.pipeline_id
    lead.updated_at = _now()

    # Record stage history
    history = CrmLeadStageHistory(
        lead_id=lead.id,
        from_stage_id=old_stage_id,
        to_stage_id=body.stage_id,
        from_stage_name=old_stage_name,
        to_stage_name=new_stage_name,
        changed_by=user.user_id,
        changed_by_name=user.full_name if hasattr(user, "full_name") else None,
        changed_at=_now(),
    )
    db.add(history)

    await db.commit()
    lead = await _get_lead(lead_id, user.company_id, db)
    return ApiResponse(success=True, data=_lead_out(lead))


@router.get("/leads/{lead_id}/stage-history")
async def get_stage_history(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadStageHistory)
        .where(CrmLeadStageHistory.lead_id == lead_id)
        .order_by(CrmLeadStageHistory.changed_at)
    )
    return ApiResponse(success=True, data=[StageHistoryOut.model_validate(h) for h in result.scalars().all()])


@router.patch("/leads/{lead_id}/status")
async def update_lead_status(lead_id: UUID, body: LeadStatusUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    if body.status not in {"open", "won", "lost"}:
        raise HTTPException(400, "status must be open, won, or lost")
    lead = await _get_lead(lead_id, user.company_id, db)
    lead.status = body.status
    if body.status in {"won", "lost"}:
        lead.closed_at = _now()
        if body.status == "lost" and body.lost_reason:
            lead.lost_reason = body.lost_reason
    lead.updated_at = _now()
    await db.commit()
    lead = await _get_lead(lead_id, user.company_id, db)
    return ApiResponse(success=True, data=_lead_out(lead))


@router.post("/leads/{lead_id}/assign")
async def assign_lead(lead_id: UUID, body: LeadAssignIn, db: DBSession, user: AuthUser):
    user.require("crm.assign")
    lead = await _get_lead(lead_id, user.company_id, db)
    by_name_map = await _resolve_user_names(db, user.company_id, {user.user_id})
    await _assign_lead(db, lead, body.assigned_to, user.user_id, by_name_map.get(user.user_id), body.note)
    await db.commit()
    lead = await _get_lead(lead_id, user.company_id, db)
    name_map = await _resolve_user_names(db, user.company_id, {lead.assigned_to, lead.assigned_by})
    return ApiResponse(success=True, data=_lead_out(lead, name_map), message="Lead assignment updated")


@router.get("/leads/{lead_id}/assignment-history")
async def get_assignment_history(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadAssignmentHistory)
        .where(CrmLeadAssignmentHistory.lead_id == lead_id)
        .order_by(CrmLeadAssignmentHistory.changed_at)
    )
    return ApiResponse(
        success=True,
        data=[LeadAssignmentHistoryOut.model_validate(h) for h in result.scalars().all()],
    )


# ── Lead Product Interest (Phase 7) ──────────────────────────────────────────
# References the real ERP product/variant master (not CrmProduct) — the
# structured version of the "Catalogue Sent" follow-up-type label, which was
# just free text with no link to which product was actually shared.

async def _lead_product_out(db, lp: CrmLeadProduct) -> LeadProductOut:
    product_name = None
    if lp.product_id:
        product_name = (await db.execute(select(Product.name).where(Product.id == lp.product_id))).scalar_one_or_none()
    variant_sku = None
    if lp.variant_id:
        variant_sku = (await db.execute(select(ProductVariant.sku).where(ProductVariant.id == lp.variant_id))).scalar_one_or_none()
    return LeadProductOut(
        id=lp.id, lead_id=lp.lead_id, product_id=lp.product_id, product_name=product_name,
        variant_id=lp.variant_id, variant_sku=variant_sku,
        quantity_interested=lp.quantity_interested, notes=lp.notes, created_at=lp.created_at,
    )


@router.get("/leads/{lead_id}/products")
async def list_lead_products(lead_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadProduct).where(CrmLeadProduct.lead_id == lead_id).order_by(CrmLeadProduct.created_at.desc())
    )
    rows = result.scalars().all()
    return ApiResponse(success=True, data=[await _lead_product_out(db, r) for r in rows])


@router.post("/leads/{lead_id}/products", status_code=201)
async def add_lead_product(lead_id: UUID, body: LeadProductCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    lead = await _get_lead(lead_id, user.company_id, db)
    lp = CrmLeadProduct(
        lead_id=lead.id, product_id=body.product_id, variant_id=body.variant_id,
        quantity_interested=body.quantity_interested, notes=body.notes,
        created_by=user.user_id, created_at=_now(),
    )
    db.add(lp)

    try:
        from app.services.whatsapp_automation import fire_event, resolve_company_name, resolve_customer_name

        product_name = ""
        if body.product_id:
            product_row = (await db.execute(select(Product.name).where(Product.id == body.product_id))).scalar_one_or_none()
            product_name = product_row or ""
        context = {
            "customer_name": await resolve_customer_name(db, lead),
            "product_name": product_name,
            "company_name": await resolve_company_name(db, lead.company_id),
        }
        await fire_event(db, lead.company_id, "catalogue_shared", context, lead=lead)
    except Exception:
        logger.warning("Failed to fire catalogue_shared WhatsApp automation", exc_info=True)

    await db.commit()
    await db.refresh(lp)
    return ApiResponse(success=True, data=await _lead_product_out(db, lp), message="Product linked to lead")


@router.delete("/leads/{lead_id}/products/{link_id}")
async def remove_lead_product(lead_id: UUID, link_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(select(CrmLeadProduct).where(CrmLeadProduct.id == link_id, CrmLeadProduct.lead_id == lead_id))
    lp = result.scalar_one_or_none()
    if not lp:
        raise HTTPException(404, "Lead product link not found")
    await db.delete(lp)
    await db.commit()
    return ApiResponse(success=True, message="Product unlinked")


@router.get("/assignable-users")
async def list_assignable_users(db: DBSession, user: AuthUser):
    """Deliberately guarded by crm.view (not admin.users) so any role that can
    see leads can also see who leads can be assigned to."""
    user.require("crm.view")
    result = await db.execute(
        select(User.id, User.full_name, User.email)
        .where(User.company_id == user.company_id, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return ApiResponse(
        success=True,
        data=[AssignableUserOut(id=uid, name=name, email=email) for uid, name, email in result.all()],
    )


# ── Activities ────────────────────────────────────────────────────────────────

@router.get("/activities")
async def list_activities(
    db: DBSession, user: AuthUser,
    lead_id: UUID | None = None, person_id: UUID | None = None,
    activity_type: str | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
    unscheduled: bool = False,
    page_size: int = 100,
):
    user.require("crm.view")
    filters = [CrmActivity.company_id == user.company_id]
    if lead_id:
        filters.append(CrmActivity.lead_id == lead_id)
    if person_id:
        filters.append(CrmActivity.person_id == person_id)
    if activity_type:
        filters.append(CrmActivity.type == activity_type)
    if unscheduled:
        filters.append(CrmActivity.schedule_from.is_(None))
    else:
        if date_from:
            filters.append(CrmActivity.schedule_from >= date_from)
        if date_to:
            filters.append(CrmActivity.schedule_from <= date_to)

    lead_alias = CrmLead
    assignee = User
    result = await db.execute(
        select(CrmActivity, lead_alias.title, CrmPerson.name, assignee.full_name)
        .outerjoin(lead_alias, lead_alias.id == CrmActivity.lead_id)
        .outerjoin(CrmPerson, CrmPerson.id == CrmActivity.person_id)
        .outerjoin(assignee, assignee.id == CrmActivity.assigned_to)
        .where(*filters)
        .order_by(CrmActivity.created_at.desc() if unscheduled else CrmActivity.schedule_from.desc())
        .limit(page_size)
    )
    data = []
    for activity, lead_title, person_name, assigned_to_name in result.all():
        out = ActivityOut.model_validate(activity)
        out.lead_title = lead_title
        out.person_name = person_name
        out.assigned_to_name = assigned_to_name
        data.append(out)
    return ApiResponse(success=True, data=data)


@router.post("/activities", status_code=201)
async def create_activity(body: ActivityCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    activity = CrmActivity(
        company_id=user.company_id, title=body.title, type=body.type,
        comment=body.comment, location=body.location,
        schedule_from=body.schedule_from, schedule_to=body.schedule_to,
        lead_id=body.lead_id, person_id=body.person_id,
        assigned_to=body.assigned_to, created_by=user.user_id,
        created_at=now, updated_at=now,
    )
    db.add(activity)
    await db.flush()
    if activity.lead_id:
        await _sync_lead_followup_fields(db, activity.lead_id)

        if activity.type.strip().lower() == "sample sent":
            try:
                from app.services.whatsapp_automation import fire_event, resolve_company_name, resolve_customer_name

                lead_for_activity = await db.get(CrmLead, activity.lead_id)
                if lead_for_activity:
                    latest_link = (
                        await db.execute(
                            select(CrmLeadProduct)
                            .where(CrmLeadProduct.lead_id == activity.lead_id, CrmLeadProduct.product_id.is_not(None))
                            .order_by(CrmLeadProduct.created_at.desc())
                            .limit(1)
                        )
                    ).scalar_one_or_none()
                    product_name = ""
                    if latest_link and latest_link.product_id:
                        product_row = (await db.execute(select(Product.name).where(Product.id == latest_link.product_id))).scalar_one_or_none()
                        product_name = product_row or ""
                    context = {
                        "customer_name": await resolve_customer_name(db, lead_for_activity),
                        "product_name": product_name,
                        "company_name": await resolve_company_name(db, user.company_id),
                    }
                    await fire_event(db, user.company_id, "sample_dispatched", context, lead=lead_for_activity)
            except Exception:
                logger.warning("Failed to fire sample_dispatched WhatsApp automation", exc_info=True)

    await db.commit()
    await db.refresh(activity)
    return ApiResponse(success=True, data=ActivityOut.model_validate(activity), message="Activity created")


@router.patch("/activities/{activity_id}")
async def update_activity(activity_id: UUID, body: ActivityUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmActivity).where(CrmActivity.id == activity_id, CrmActivity.company_id == user.company_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(404, "Activity not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(activity, field, val)
    activity.updated_at = _now()
    if activity.lead_id:
        await db.flush()
        await _sync_lead_followup_fields(db, activity.lead_id)
    await db.commit()
    await db.refresh(activity)
    return ApiResponse(success=True, data=ActivityOut.model_validate(activity))


@router.patch("/activities/{activity_id}/done")
async def mark_activity_done(activity_id: UUID, db: DBSession, user: AuthUser, body: ActivityDoneUpdate | None = None):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmActivity).where(CrmActivity.id == activity_id, CrmActivity.company_id == user.company_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(404, "Activity not found")
    now = _now()
    activity.is_done = body.is_done if body is not None else True
    activity.updated_at = now

    if activity.lead_id and body is not None and activity.is_done:
        lead_result = await db.execute(select(CrmLead).where(CrmLead.id == activity.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            if body.outcome is not None:
                lead.contact_outcome = body.outcome
            if body.next_action is not None:
                lead.next_action = body.next_action
            if lead.first_contacted_at is None:
                # Set once, never overwritten — distinct from last_contacted_at
                # below, which updates on every contact. Response-time
                # reporting needs the FIRST contact specifically.
                lead.first_contacted_at = now
            lead.last_contacted_at = now
            lead.updated_at = now

            if body.next_follow_up_at:
                next_activity = CrmActivity(
                    company_id=user.company_id,
                    title=f"Follow-up: {activity.title}",
                    type=body.next_follow_up_type or activity.type,
                    comment=body.next_follow_up_notes or body.next_follow_up_reason,
                    schedule_from=body.next_follow_up_at,
                    lead_id=activity.lead_id,
                    assigned_to=activity.assigned_to,
                    created_by=user.user_id,
                    created_at=now, updated_at=now,
                )
                db.add(next_activity)

    if activity.lead_id:
        await db.flush()
        await _sync_lead_followup_fields(db, activity.lead_id)
    await db.commit()
    await db.refresh(activity)
    return ApiResponse(success=True, data=ActivityOut.model_validate(activity))


@router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmActivity).where(CrmActivity.id == activity_id, CrmActivity.company_id == user.company_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(404, "Activity not found")
    lead_id = activity.lead_id
    await db.delete(activity)
    if lead_id:
        await db.flush()
        await _sync_lead_followup_fields(db, lead_id)
    await db.commit()
    return ApiResponse(success=True, message="Activity deleted")


@router.get("/follow-up-types")
async def list_follow_up_types(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmFollowUpType).where(CrmFollowUpType.company_id == user.company_id).order_by(CrmFollowUpType.name)
    )
    return ApiResponse(success=True, data=[FollowUpTypeOut.model_validate(t) for t in result.scalars().all()])


# ── Tasks (Phase 3) ──────────────────────────────────────────────────────────

def _task_out(task: CrmTask, name_map: dict[UUID, str] | None = None, lead_titles: dict[UUID, str] | None = None,
              customer_names: dict[UUID, str] | None = None) -> TaskOut:
    name_map = name_map or {}
    lead_titles = lead_titles or {}
    customer_names = customer_names or {}
    return TaskOut(
        id=task.id, company_id=task.company_id, title=task.title, notes=task.notes,
        lead_id=task.lead_id, lead_title=lead_titles.get(task.lead_id),
        customer_id=task.customer_id, customer_name=customer_names.get(task.customer_id),
        assigned_to=task.assigned_to, assigned_to_name=name_map.get(task.assigned_to),
        due_at=task.due_at, priority=task.priority, status=task.status, source=task.source,
        created_by=task.created_by, created_by_name=name_map.get(task.created_by),
        completed_at=task.completed_at, created_at=task.created_at, updated_at=task.updated_at,
    )


async def _enrich_tasks(db, company_id: UUID, tasks: list[CrmTask]) -> list[TaskOut]:
    user_ids = {t.assigned_to for t in tasks} | {t.created_by for t in tasks}
    name_map = await _resolve_user_names(db, company_id, user_ids)

    lead_ids = {t.lead_id for t in tasks if t.lead_id}
    lead_titles: dict[UUID, str] = {}
    if lead_ids:
        res = await db.execute(select(CrmLead.id, CrmLead.title).where(CrmLead.id.in_(lead_ids)))
        lead_titles = {lid: title for lid, title in res.all()}

    customer_ids = {t.customer_id for t in tasks if t.customer_id}
    customer_names: dict[UUID, str] = {}
    if customer_ids:
        res = await db.execute(select(Customer.id, Customer.legal_name).where(Customer.id.in_(customer_ids)))
        customer_names = {cid: name for cid, name in res.all()}

    return [_task_out(t, name_map, lead_titles, customer_names) for t in tasks]


@router.get("/tasks")
async def list_tasks(
    db: DBSession, user: AuthUser,
    assigned_to: UUID | None = None, status: str | None = None, priority: str | None = None,
    lead_id: UUID | None = None, overdue: bool = False,
    page: int = 1, page_size: int = 50,
):
    user.require("crm.view")
    filters = [CrmTask.company_id == user.company_id]
    if assigned_to:
        filters.append(CrmTask.assigned_to == assigned_to)
    if status:
        filters.append(CrmTask.status == status)
    if priority:
        filters.append(CrmTask.priority == priority)
    if lead_id:
        filters.append(CrmTask.lead_id == lead_id)
    if overdue:
        filters.append(CrmTask.status.in_(["pending", "in_progress"]))
        filters.append(CrmTask.due_at < _now())

    total_result = await db.execute(select(func.count(CrmTask.id)).where(*filters))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CrmTask).where(*filters)
        .order_by(CrmTask.due_at.asc().nulls_last(), CrmTask.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()
    data = await _enrich_tasks(db, user.company_id, tasks)
    return ApiResponse(success=True, data=data, meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/tasks", status_code=201)
async def create_task(body: TaskCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    task = CrmTask(
        company_id=user.company_id, title=body.title, notes=body.notes,
        lead_id=body.lead_id, customer_id=body.customer_id, assigned_to=body.assigned_to,
        due_at=body.due_at, priority=body.priority, source=body.source,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    data = await _enrich_tasks(db, user.company_id, [task])
    return ApiResponse(success=True, data=data[0], message="Task created")


@router.patch("/tasks/{task_id}")
async def update_task(task_id: UUID, body: TaskUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(select(CrmTask).where(CrmTask.id == task_id, CrmTask.company_id == user.company_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(task, field, val)
    task.updated_at = _now()
    await db.commit()
    await db.refresh(task)
    data = await _enrich_tasks(db, user.company_id, [task])
    return ApiResponse(success=True, data=data[0])


@router.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: UUID, db: DBSession, user: AuthUser, body: TaskCompleteIn | None = None):
    user.require("crm.edit")
    result = await db.execute(select(CrmTask).where(CrmTask.id == task_id, CrmTask.company_id == user.company_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    now = _now()
    task.status = "completed"
    task.completed_at = now
    task.updated_at = now
    if body is not None and body.notes:
        task.notes = f"{task.notes}\n{body.notes}" if task.notes else body.notes
    await db.commit()
    await db.refresh(task)
    data = await _enrich_tasks(db, user.company_id, [task])
    return ApiResponse(success=True, data=data[0], message="Task completed")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(select(CrmTask).where(CrmTask.id == task_id, CrmTask.company_id == user.company_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
    return ApiResponse(success=True, message="Task deleted")


# ── Ad Spend (Phase 5) ───────────────────────────────────────────────────────

def _ad_spend_out(spend: CrmAdSpend, name_map: dict[UUID, str] | None = None,
                   source_names: dict[UUID, str] | None = None) -> AdSpendOut:
    name_map = name_map or {}
    source_names = source_names or {}
    return AdSpendOut(
        id=spend.id, company_id=spend.company_id,
        source_id=spend.source_id, source_name=source_names.get(spend.source_id),
        campaign=spend.campaign, campaign_id=spend.campaign_id, ad_set=spend.ad_set,
        period_start=spend.period_start, period_end=spend.period_end,
        amount=spend.amount, impressions=spend.impressions, clicks=spend.clicks,
        source=spend.source, notes=spend.notes,
        created_by=spend.created_by, created_by_name=name_map.get(spend.created_by),
        created_at=spend.created_at,
    )


async def _enrich_ad_spend(db, company_id: UUID, rows: list[CrmAdSpend]) -> list[AdSpendOut]:
    name_map = await _resolve_user_names(db, company_id, {r.created_by for r in rows})
    source_ids = {r.source_id for r in rows if r.source_id}
    source_names: dict[UUID, str] = {}
    if source_ids:
        res = await db.execute(select(CrmLeadSource.id, CrmLeadSource.name).where(CrmLeadSource.id.in_(source_ids)))
        source_names = {sid: name for sid, name in res.all()}
    return [_ad_spend_out(r, name_map, source_names) for r in rows]


@router.get("/ad-spend")
async def list_ad_spend(
    db: DBSession, user: AuthUser,
    source_id: UUID | None = None, campaign: str | None = None,
    from_date: date | None = None, to_date: date | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("crm.view")
    filters = [CrmAdSpend.company_id == user.company_id]
    if source_id:
        filters.append(CrmAdSpend.source_id == source_id)
    if campaign:
        filters.append(CrmAdSpend.campaign.ilike(f"%{campaign}%"))
    if from_date:
        filters.append(CrmAdSpend.period_end >= from_date)
    if to_date:
        filters.append(CrmAdSpend.period_start <= to_date)

    total_result = await db.execute(select(func.count(CrmAdSpend.id)).where(*filters))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CrmAdSpend).where(*filters)
        .order_by(CrmAdSpend.period_start.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    data = await _enrich_ad_spend(db, user.company_id, rows)
    return ApiResponse(success=True, data=data, meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/ad-spend", status_code=201)
async def create_ad_spend(body: AdSpendCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    if body.period_end < body.period_start:
        raise HTTPException(400, "period_end cannot be before period_start")
    spend = CrmAdSpend(
        company_id=user.company_id, source_id=body.source_id, campaign=body.campaign,
        campaign_id=body.campaign_id, ad_set=body.ad_set,
        period_start=body.period_start, period_end=body.period_end, amount=body.amount,
        impressions=body.impressions, clicks=body.clicks,
        notes=body.notes, created_by=user.user_id, created_at=_now(),
    )
    db.add(spend)
    await db.commit()
    await db.refresh(spend)
    data = await _enrich_ad_spend(db, user.company_id, [spend])
    return ApiResponse(success=True, data=data[0], message="Ad spend logged")


@router.patch("/ad-spend/{spend_id}")
async def update_ad_spend(spend_id: UUID, body: AdSpendUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(select(CrmAdSpend).where(CrmAdSpend.id == spend_id, CrmAdSpend.company_id == user.company_id))
    spend = result.scalar_one_or_none()
    if not spend:
        raise HTTPException(404, "Ad spend entry not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(spend, field, val)
    if spend.period_end < spend.period_start:
        raise HTTPException(400, "period_end cannot be before period_start")
    await db.commit()
    await db.refresh(spend)
    data = await _enrich_ad_spend(db, user.company_id, [spend])
    return ApiResponse(success=True, data=data[0], message="Ad spend updated")


@router.delete("/ad-spend/{spend_id}")
async def delete_ad_spend(spend_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    result = await db.execute(select(CrmAdSpend).where(CrmAdSpend.id == spend_id, CrmAdSpend.company_id == user.company_id))
    spend = result.scalar_one_or_none()
    if not spend:
        raise HTTPException(404, "Ad spend entry not found")
    await db.delete(spend)
    await db.commit()
    return ApiResponse(success=True, message="Ad spend entry deleted")


def _parse_int(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


@router.post("/ad-spend/import", status_code=201)
async def import_ad_spend_csv(db: DBSession, user: AuthUser, file: UploadFile):
    """CSV import for ad spend — mirrors import_leads_csv's shape (same
    UploadFile/decode/DictReader/row-try-except pattern). No persisted
    import-history record (unlike CrmLeadImport) — the summary is returned
    inline, which is all this phase's CSV import warrants."""
    user.require("crm.create")

    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(400, "File must be a CSV (.csv extension required)")

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_content = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    raw_rows = list(reader)
    if len(raw_rows) > 1000:
        raise HTTPException(400, "CSV exceeds 1000-row limit")
    rows = [{k.lower().strip(): v for k, v in row.items()} for row in raw_rows]

    # Resolve platform names -> source_id, auto-creating unseen ones (same
    # spirit as Phase 4 making sources user-manageable — a CSV from a new
    # ad platform shouldn't fail just because nobody pre-registered it).
    existing_result = await db.execute(
        select(CrmLeadSource).where(CrmLeadSource.company_id == user.company_id)
    )
    source_by_name = {s.name.strip().lower(): s.id for s in existing_result.scalars().all()}

    now = _now()
    imported = 0
    errors: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        platform = (row.get("platform") or "").strip()
        period_start = _parse_date(row.get("period_start", ""))
        period_end = _parse_date(row.get("period_end", ""))
        amount = _parse_decimal(row.get("amount", ""))
        if not platform:
            errors.append({"row": idx, "error": "Missing required field: platform"})
            continue
        if not period_start or not period_end:
            errors.append({"row": idx, "error": "Missing or invalid period_start/period_end (expected YYYY-MM-DD)"})
            continue
        if amount <= 0:
            errors.append({"row": idx, "error": "amount must be greater than 0"})
            continue
        if period_end < period_start:
            errors.append({"row": idx, "error": "period_end cannot be before period_start"})
            continue
        try:
            key = platform.lower()
            source_id = source_by_name.get(key)
            if not source_id:
                new_source = CrmLeadSource(company_id=user.company_id, name=platform, created_at=now)
                db.add(new_source)
                await db.flush()
                source_id = new_source.id
                source_by_name[key] = source_id

            spend = CrmAdSpend(
                company_id=user.company_id, source_id=source_id,
                campaign=row.get("campaign", "").strip() or None,
                campaign_id=row.get("campaign_id", "").strip() or None,
                ad_set=row.get("ad_set", "").strip() or None,
                period_start=period_start, period_end=period_end, amount=amount,
                impressions=_parse_int(row.get("impressions", "")),
                clicks=_parse_int(row.get("clicks", "")),
                source="manual", notes=row.get("notes", "").strip() or None,
                created_by=user.user_id, created_at=now,
            )
            db.add(spend)
            imported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "error": str(exc)})

    await db.commit()
    return ApiResponse(
        success=True,
        data={"total_rows": len(rows), "imported": imported, "failed": len(errors), "errors": errors},
        message=f"Imported {imported} of {len(rows)} row(s)",
    )


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/products")
async def list_products(db: DBSession, user: AuthUser, is_active: bool = True, search: str | None = None):
    user.require("crm.view")
    q = select(CrmProduct).where(CrmProduct.company_id == user.company_id, CrmProduct.is_active == is_active)
    if search:
        q = q.where(CrmProduct.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(CrmProduct.name))
    return ApiResponse(success=True, data=[ProductOut.model_validate(p) for p in result.scalars().all()])


@router.post("/products", status_code=201)
async def create_product(body: ProductCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    product = CrmProduct(
        company_id=user.company_id, name=body.name, description=body.description,
        sku=body.sku, price=body.price, currency=body.currency, unit=body.unit,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ApiResponse(success=True, data=ProductOut.model_validate(product), message="Product created")


@router.patch("/products/{product_id}")
async def update_product(product_id: UUID, body: ProductUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmProduct).where(CrmProduct.id == product_id, CrmProduct.company_id == user.company_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(product, field, val)
    product.updated_at = _now()
    await db.commit()
    await db.refresh(product)
    return ApiResponse(success=True, data=ProductOut.model_validate(product))


# ── Quotes ────────────────────────────────────────────────────────────────────

_QUOTE_OPTS = [
    selectinload(CrmQuote.lead),
    selectinload(CrmQuote.person),
    selectinload(CrmQuote.organization),
    selectinload(CrmQuote.items).selectinload(CrmQuoteItem.product),
]


def _quote_out(quote: CrmQuote) -> QuoteOut:
    return QuoteOut(
        id=quote.id, company_id=quote.company_id, quote_number=quote.quote_number,
        title=quote.title, status=quote.status,
        lead_id=quote.lead_id, lead_title=quote.lead.title if quote.lead else None,
        person_id=quote.person_id, person_name=quote.person.name if quote.person else None,
        organization_id=quote.organization_id, org_name=quote.organization.name if quote.organization else None,
        valid_until=quote.valid_until, currency=quote.currency,
        subtotal=quote.subtotal, discount_percent=quote.discount_percent,
        discount_amount=quote.discount_amount, tax_amount=quote.tax_amount, total_amount=quote.total_amount,
        notes=quote.notes, terms=quote.terms, sales_order_id=quote.sales_order_id,
        assigned_to=quote.assigned_to, created_by=quote.created_by,
        sent_at=quote.sent_at, accepted_at=quote.accepted_at,
        created_at=quote.created_at, updated_at=quote.updated_at,
        items=[QuoteItemOut.model_validate(i) for i in (quote.items or [])],
    )


def _quote_list_out(quote: CrmQuote) -> QuoteListOut:
    return QuoteListOut(
        id=quote.id, quote_number=quote.quote_number, title=quote.title, status=quote.status,
        lead_title=quote.lead.title if quote.lead else None,
        person_name=quote.person.name if quote.person else None,
        org_name=quote.organization.name if quote.organization else None,
        total_amount=quote.total_amount, valid_until=quote.valid_until, created_at=quote.created_at,
    )


async def _get_quote(quote_id: UUID, company_id: UUID, db) -> CrmQuote:
    result = await db.execute(
        select(CrmQuote).options(*_QUOTE_OPTS)
        .where(CrmQuote.id == quote_id, CrmQuote.company_id == company_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, "Quote not found")
    return quote


def _build_items(items_in):
    rows = []
    subtotal = Decimal("0")
    for idx, item in enumerate(items_in):
        total = round(item.quantity * item.unit_price * (1 - item.discount_percent / 100), 4)
        subtotal += total
        rows.append({
            "product_id": item.product_id,
            "erp_product_id": item.erp_product_id, "erp_variant_id": item.erp_variant_id,
            "name": item.name, "description": item.description,
            "quantity": item.quantity, "unit_price": item.unit_price,
            "discount_percent": item.discount_percent, "total": total, "sort_order": idx,
        })
    return rows, subtotal


@router.get("/quotes")
async def list_quotes(
    db: DBSession, user: AuthUser,
    lead_id: UUID | None = None, status: str | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("crm.view")
    filters = [CrmQuote.company_id == user.company_id]
    if lead_id:
        filters.append(CrmQuote.lead_id == lead_id)
    if status:
        filters.append(CrmQuote.status == status)

    total_result = await db.execute(select(func.count(CrmQuote.id)).where(*filters))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CrmQuote).options(*_QUOTE_OPTS).where(*filters)
        .order_by(CrmQuote.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    quotes = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[_quote_list_out(q) for q in quotes],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/quotes", status_code=201)
async def create_quote(body: QuoteCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    seq_result = await db.execute(text("SELECT nextval('crm_quote_seq')"))
    quote_number = f"QUOTE-{seq_result.scalar()}"
    now = _now()
    rows, subtotal = _build_items(body.items)
    discount_amount = round(subtotal * body.discount_percent / 100, 4)
    total_amount = subtotal - discount_amount + body.tax_amount
    quote = CrmQuote(
        company_id=user.company_id, quote_number=quote_number, title=body.title,
        status="draft", lead_id=body.lead_id, person_id=body.person_id,
        organization_id=body.organization_id, valid_until=body.valid_until,
        currency=body.currency, subtotal=subtotal, discount_percent=body.discount_percent,
        discount_amount=discount_amount, tax_amount=body.tax_amount, total_amount=total_amount,
        notes=body.notes, terms=body.terms, assigned_to=body.assigned_to,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(quote)
    await db.flush()
    for item_data in rows:
        db.add(CrmQuoteItem(quote_id=quote.id, **item_data))
    if quote.lead_id:
        try:
            from app.services.whatsapp_automation import fire_event, resolve_company_name, resolve_customer_name

            lead_for_quote = await db.get(CrmLead, quote.lead_id)
            if lead_for_quote:
                context = {
                    "customer_name": await resolve_customer_name(db, lead_for_quote),
                    "quotation_number": quote.quote_number,
                    "company_name": await resolve_company_name(db, user.company_id),
                }
                await fire_event(db, user.company_id, "quotation_generated", context, lead=lead_for_quote)
        except Exception:
            logger.warning("Failed to fire quotation_generated WhatsApp automation", exc_info=True)

    await db.commit()
    quote = await _get_quote(quote.id, user.company_id, db)
    return ApiResponse(success=True, data=_quote_out(quote), message="Quote created")


@router.get("/quotes/{quote_id}")
async def get_quote(quote_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    quote = await _get_quote(quote_id, user.company_id, db)
    return ApiResponse(success=True, data=_quote_out(quote))


@router.patch("/quotes/{quote_id}")
async def update_quote(quote_id: UUID, body: QuoteUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    quote = await _get_quote(quote_id, user.company_id, db)
    if quote.status in {"accepted", "declined"}:
        raise HTTPException(400, "Cannot edit an accepted or declined quote")
    items_provided = "items" in body.model_fields_set
    for field, val in body.model_dump(exclude_unset=True, exclude={"items"}).items():
        setattr(quote, field, val)
    if items_provided:
        await db.execute(delete(CrmQuoteItem).where(CrmQuoteItem.quote_id == quote.id))
        rows, subtotal = _build_items(body.items or [])
        quote.subtotal = subtotal
        await db.flush()
        for item_data in rows:
            db.add(CrmQuoteItem(quote_id=quote.id, **item_data))
    else:
        subtotal = quote.subtotal
    discount_amount = round(subtotal * quote.discount_percent / 100, 4)
    quote.discount_amount = discount_amount
    quote.total_amount = subtotal - discount_amount + quote.tax_amount
    quote.updated_at = _now()
    await db.commit()
    quote = await _get_quote(quote_id, user.company_id, db)
    return ApiResponse(success=True, data=_quote_out(quote))


@router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.delete")
    quote = await _get_quote(quote_id, user.company_id, db)
    if quote.status in {"accepted", "declined"}:
        raise HTTPException(400, "Cannot delete an accepted or declined quote")
    await db.delete(quote)
    await db.commit()
    return ApiResponse(success=True, message="Quote deleted")


@router.patch("/quotes/{quote_id}/status")
async def update_quote_status(quote_id: UUID, body: QuoteStatusUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    valid_statuses = {"sent", "accepted", "declined", "expired"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"status must be one of: {', '.join(sorted(valid_statuses))}")
    quote = await _get_quote(quote_id, user.company_id, db)
    quote.status = body.status
    now = _now()
    if body.status == "sent" and not quote.sent_at:
        quote.sent_at = now
    if body.status == "accepted" and not quote.accepted_at:
        quote.accepted_at = now
    quote.updated_at = now
    await db.commit()
    quote = await _get_quote(quote_id, user.company_id, db)
    return ApiResponse(success=True, data=_quote_out(quote))


@router.post("/quotes/{quote_id}/duplicate", status_code=201)
async def duplicate_quote(quote_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.create")
    quote = await _get_quote(quote_id, user.company_id, db)
    seq_result = await db.execute(text("SELECT nextval('crm_quote_seq')"))
    quote_number = f"QUOTE-{seq_result.scalar()}"
    now = _now()
    new_quote = CrmQuote(
        company_id=user.company_id, quote_number=quote_number, title=quote.title,
        status="draft", lead_id=quote.lead_id, person_id=quote.person_id,
        organization_id=quote.organization_id, valid_until=quote.valid_until,
        currency=quote.currency, subtotal=quote.subtotal, discount_percent=quote.discount_percent,
        discount_amount=quote.discount_amount, tax_amount=quote.tax_amount, total_amount=quote.total_amount,
        notes=quote.notes, terms=quote.terms, assigned_to=quote.assigned_to,
        created_by=user.user_id, created_at=now, updated_at=now,
    )
    db.add(new_quote)
    await db.flush()
    for item in quote.items:
        db.add(CrmQuoteItem(
            quote_id=new_quote.id, product_id=item.product_id,
            erp_product_id=item.erp_product_id, erp_variant_id=item.erp_variant_id,
            name=item.name,
            description=item.description, quantity=item.quantity, unit_price=item.unit_price,
            discount_percent=item.discount_percent, total=item.total, sort_order=item.sort_order,
        ))
    await db.commit()
    new_quote = await _get_quote(new_quote.id, user.company_id, db)
    return ApiResponse(success=True, data=_quote_out(new_quote), message="Quote duplicated")


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/reports/sales-kpis")
async def sales_kpis(
    db: DBSession, user: AuthUser,
    date_from: date, date_to: date,
    utc_offset_minutes: int = 0,
    pipeline_id: UUID | None = None, assigned_to: UUID | None = None, source_id: UUID | None = None,
):
    user.require("crm.view")
    if date_to < date_from:
        raise HTTPException(400, "date_to must be on or after date_from")
    prev_from, prev_to = previous_period(date_from, date_to)
    shared = dict(
        utc_offset_minutes=utc_offset_minutes, pipeline_id=pipeline_id,
        assigned_to=assigned_to, source_id=source_id,
    )
    current_facts, unconfigured = await load_cohort(
        db, user.company_id, CohortFilter(date_from=date_from, date_to=date_to, **shared)
    )
    previous_facts, _ = await load_cohort(
        db, user.company_id, CohortFilter(date_from=prev_from, date_to=prev_to, **shared)
    )
    current = summarize(current_facts)
    previous = summarize(previous_facts)
    return ApiResponse(success=True, data={
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "previous_period": {"from": prev_from.isoformat(), "to": prev_to.isoformat()},
        "current": current.to_dict(),
        "previous": previous.to_dict(),
        "comparisons": compare(current, previous),
        "leads_in_pipelines_without_qualification_stage": unconfigured,
    })


@router.get("/reports/lead-quality")
async def lead_quality(
    db: DBSession, user: AuthUser,
    date_from: date, date_to: date,
    utc_offset_minutes: int = 0,
    pipeline_id: UUID | None = None, assigned_to: UUID | None = None, source_id: UUID | None = None,
):
    user.require("crm.view")
    if date_to < date_from:
        raise HTTPException(400, "date_to must be on or after date_from")
    tiers = await lead_quality_breakdown(db, user.company_id, CohortFilter(
        date_from=date_from, date_to=date_to, utc_offset_minutes=utc_offset_minutes,
        pipeline_id=pipeline_id, assigned_to=assigned_to, source_id=source_id,
    ))
    return ApiResponse(success=True, data={
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "tiers": tiers,
        "total_leads": sum(t["leads"] for t in tiers),
    })


@router.get("/reports/open-pipeline")
async def open_pipeline(
    db: DBSession, user: AuthUser,
    utc_offset_minutes: int = 0,
    pipeline_id: UUID | None = None, assigned_to: UUID | None = None, source_id: UUID | None = None,
):
    user.require("crm.view")
    data = await load_open_pipeline(
        db, user.company_id,
        OpenPipelineFilter(pipeline_id=pipeline_id, assigned_to=assigned_to, source_id=source_id),
        _now(), utc_offset_minutes,
    )
    return ApiResponse(success=True, data=data)


@router.get("/dashboard")
async def crm_dashboard(db: DBSession, user: AuthUser):
    user.require("crm.view")
    now = _now()

    # Pipeline summary: count + sum open leads per stage, across all company pipelines
    pipeline_rows = await db.execute(
        select(
            CrmPipelineStage.id,
            CrmPipelineStage.name,
            CrmPipelineStage.sort_order,
            CrmPipelineStage.is_won,
            CrmPipelineStage.is_lost,
            func.count(CrmLead.id).label("lead_count"),
            func.coalesce(func.sum(CrmLead.lead_value), Decimal("0")).label("total_value"),
        )
        .join(CrmPipeline, CrmPipeline.id == CrmPipelineStage.pipeline_id)
        .outerjoin(
            CrmLead,
            and_(
                CrmLead.stage_id == CrmPipelineStage.id,
                CrmLead.status == "open",
                CrmLead.company_id == user.company_id,
            ),
        )
        .where(CrmPipeline.company_id == user.company_id)
        .group_by(
            CrmPipelineStage.id,
            CrmPipelineStage.name,
            CrmPipelineStage.sort_order,
            CrmPipelineStage.is_won,
            CrmPipelineStage.is_lost,
        )
        .order_by(CrmPipelineStage.sort_order)
    )
    pipeline_summary = [
        {
            "stage_id": str(row.id),
            "stage_name": row.name,
            "sort_order": row.sort_order,
            "is_won": row.is_won,
            "is_lost": row.is_lost,
            "lead_count": row.lead_count,
            "total_value": float(row.total_value),
        }
        for row in pipeline_rows
    ]

    # Status counts
    status_rows = await db.execute(
        select(CrmLead.status, func.count(CrmLead.id).label("cnt"))
        .where(CrmLead.company_id == user.company_id)
        .group_by(CrmLead.status)
    )
    status_counts: dict[str, int] = {"open": 0, "won": 0, "lost": 0}
    for row in status_rows:
        if row.status in status_counts:
            status_counts[row.status] = row.cnt

    # Activities due in next 24 hours (not yet overdue)
    due_result = await db.execute(
        select(func.count(CrmActivity.id))
        .where(
            CrmActivity.company_id == user.company_id,
            CrmActivity.is_done.is_(False),
            CrmActivity.schedule_from >= now,
            CrmActivity.schedule_from <= now + timedelta(hours=24),
        )
    )
    activities_due: int = due_result.scalar() or 0

    # Activities overdue (past due, not done)
    overdue_result = await db.execute(
        select(func.count(CrmActivity.id))
        .where(
            CrmActivity.company_id == user.company_id,
            CrmActivity.is_done.is_(False),
            CrmActivity.schedule_from < now,
        )
    )
    activities_overdue: int = overdue_result.scalar() or 0

    # Leads with a follow-up due today / overdue (list, not just a count) —
    # surfaces *which* leads need action, sourced from CrmLead's synced
    # follow-up fields rather than re-querying activities.
    def _followup_rows(rows) -> list[dict]:
        return [
            {
                "lead_id": str(lead.id), "lead_title": lead.title,
                "next_follow_up_at": lead.next_follow_up_at.isoformat() if lead.next_follow_up_at else None,
                "follow_up_type": lead.follow_up_type,
                "assigned_to_name": assignee_name,
            }
            for lead, assignee_name in rows
        ]

    today_result = await db.execute(
        select(CrmLead, User.full_name)
        .outerjoin(User, User.id == CrmLead.assigned_to)
        .where(
            CrmLead.company_id == user.company_id,
            CrmLead.follow_up_status == "scheduled",
            CrmLead.next_follow_up_at >= now,
            CrmLead.next_follow_up_at <= now + timedelta(hours=24),
        )
        .order_by(CrmLead.next_follow_up_at.asc())
        .limit(10)
    )
    follow_ups_today = _followup_rows(today_result.all())

    followup_overdue_result = await db.execute(
        select(CrmLead, User.full_name)
        .outerjoin(User, User.id == CrmLead.assigned_to)
        .where(
            CrmLead.company_id == user.company_id,
            CrmLead.follow_up_status == "scheduled",
            CrmLead.next_follow_up_at < now,
        )
        .order_by(CrmLead.next_follow_up_at.asc())
        .limit(10)
    )
    follow_ups_overdue = _followup_rows(followup_overdue_result.all())

    # My Tasks — personal (assigned to the requesting user), not company-wide
    def _task_rows(rows) -> list[dict]:
        return [
            {
                "id": str(t.id), "title": t.title,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "priority": t.priority,
                "lead_id": str(t.lead_id) if t.lead_id else None,
            }
            for t in rows
        ]

    my_tasks_today_result = await db.execute(
        select(CrmTask)
        .where(
            CrmTask.company_id == user.company_id,
            CrmTask.assigned_to == user.user_id,
            CrmTask.status.in_(["pending", "in_progress"]),
            CrmTask.due_at >= now, CrmTask.due_at <= now + timedelta(hours=24),
        )
        .order_by(CrmTask.due_at.asc())
        .limit(10)
    )
    my_tasks_today = _task_rows(my_tasks_today_result.scalars().all())

    my_tasks_overdue_result = await db.execute(
        select(CrmTask)
        .where(
            CrmTask.company_id == user.company_id,
            CrmTask.assigned_to == user.user_id,
            CrmTask.status.in_(["pending", "in_progress"]),
            CrmTask.due_at < now,
        )
        .order_by(CrmTask.due_at.asc())
        .limit(10)
    )
    my_tasks_overdue = _task_rows(my_tasks_overdue_result.scalars().all())

    my_tasks_completed_today_result = await db.execute(
        select(func.count(CrmTask.id))
        .where(
            CrmTask.company_id == user.company_id,
            CrmTask.assigned_to == user.user_id,
            CrmTask.status == "completed",
            CrmTask.completed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        )
    )
    my_tasks_completed_today: int = my_tasks_completed_today_result.scalar() or 0

    # Last 5 created leads with stage name
    recent_result = await db.execute(
        select(CrmLead, CrmPipelineStage.name.label("stage_label"))
        .outerjoin(CrmPipelineStage, CrmPipelineStage.id == CrmLead.stage_id)
        .where(CrmLead.company_id == user.company_id)
        .order_by(CrmLead.created_at.desc())
        .limit(5)
    )
    recent_leads = [
        {
            "id": str(row.CrmLead.id),
            "title": row.CrmLead.title,
            "status": row.CrmLead.status,
            "stage_name": row.stage_label,
            "lead_value": float(row.CrmLead.lead_value or 0),
            "created_at": row.CrmLead.created_at.isoformat() if row.CrmLead.created_at else None,
        }
        for row in recent_result
    ]

    # Conversion rate
    won = status_counts["won"]
    lost = status_counts["lost"]
    conversion_rate = round(won / (won + lost) * 100, 1) if (won + lost) > 0 else 0.0

    # Total pipeline value (open leads)
    pipeline_val_result = await db.execute(
        select(func.coalesce(func.sum(CrmLead.lead_value), Decimal("0")))
        .where(CrmLead.company_id == user.company_id, CrmLead.status == "open")
    )
    total_pipeline_value = float(pipeline_val_result.scalar() or 0)

    # Won value last 30 days
    won_val_result = await db.execute(
        select(func.coalesce(func.sum(CrmLead.lead_value), Decimal("0")))
        .where(
            CrmLead.company_id == user.company_id,
            CrmLead.status == "won",
            CrmLead.closed_at >= now - timedelta(days=30),
        )
    )
    won_value_30d = float(won_val_result.scalar() or 0)

    return ApiResponse(
        success=True,
        data={
            "pipeline_summary": pipeline_summary,
            "status_counts": status_counts,
            "activities_due": activities_due,
            "activities_overdue": activities_overdue,
            "follow_ups_today": follow_ups_today,
            "follow_ups_overdue": follow_ups_overdue,
            "my_tasks_today": my_tasks_today,
            "my_tasks_overdue": my_tasks_overdue,
            "my_tasks_completed_today": my_tasks_completed_today,
            "recent_leads": recent_leads,
            "conversion_rate": conversion_rate,
            "total_pipeline_value": total_pipeline_value,
            "won_value_30d": won_value_30d,
        },
    )


# ── Lead → Sales Order Conversion ─────────────────────────────────────────────

@router.post("/leads/{lead_id}/convert")
async def convert_lead_to_sales_order(lead_id: UUID, body: LeadConvertIn, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    user.require("sales.create")

    lead = await _get_lead(lead_id, user.company_id, db)

    if lead.status == "won" and lead.sales_order_id is not None:
        raise HTTPException(400, "Lead already converted")

    from app.schemas.sales import SalesOrderCreate
    from app.services.sales import SalesService

    notes_text = f"Converted from CRM Lead: {lead.title}"
    if body.notes:
        notes_text = notes_text + "\n" + body.notes

    so_create = SalesOrderCreate(
        customer_id=body.customer_id,
        quotation_id=None,
        order_date=body.order_date,
        expected_delivery=body.expected_delivery,
        notes=notes_text,
        intrastate=body.intrastate,
        items=[],
    )

    so = await SalesService(db).create_sales_order(so_create, user.company_id, user.user_id)

    lead.status = "won"
    lead.sales_order_id = so.id
    lead.closed_at = _now()
    lead.updated_at = _now()
    await db.commit()

    return ApiResponse(
        success=True,
        data={"sales_order_id": str(so.id), "order_number": so.order_number},
    )


# ── SMTP Config ───────────────────────────────────────────────────────────────

async def _get_smtp_config(company_id: UUID, db) -> CrmSmtpConfig | None:
    result = await db.execute(
        select(CrmSmtpConfig).where(CrmSmtpConfig.company_id == company_id)
    )
    return result.scalar_one_or_none()


def _smtp_transport_kwargs(cfg: CrmSmtpConfig, password: str) -> dict:
    # Users often paste a URL ("https://smtp.gmail.com") into the host field;
    # aiosmtplib needs a bare hostname.
    host = cfg.host.strip()
    for prefix in ("https://", "http://", "smtps://", "smtp://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix):]
    host = host.split("/")[0].strip()
    # Port 465 is implicit TLS (use_tls); any other port uses STARTTLS (start_tls)
    # when encryption is enabled, e.g. Gmail on 587.
    implicit_tls = cfg.port == 465
    return {
        "hostname": host,
        "port": cfg.port,
        "username": cfg.username,
        "password": password,
        "use_tls": implicit_tls and cfg.use_tls,
        "start_tls": (not implicit_tls) and cfg.use_tls,
    }


@router.get("/email/smtp-config")
async def get_smtp_config(db: DBSession, user: AuthUser):
    user.require("crm.view")
    cfg = await _get_smtp_config(user.company_id, db)
    if not cfg:
        raise HTTPException(404, "SMTP not configured")
    out = SmtpConfigOut.model_validate(cfg)
    # Mask password — never return plaintext
    return ApiResponse(success=True, data={**out.model_dump(), "password": "••••••••"})


@router.post("/email/smtp-config", status_code=200)
async def upsert_smtp_config(body: SmtpConfigCreate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    now = _now()
    cfg = await _get_smtp_config(user.company_id, db)
    if cfg:
        cfg.host = body.host
        cfg.port = body.port
        cfg.username = body.username
        cfg.password_encrypted = _enc(body.password)
        cfg.from_name = body.from_name
        cfg.from_email = body.from_email
        cfg.use_tls = body.use_tls
        cfg.is_verified = False
        cfg.updated_at = now
    else:
        cfg = CrmSmtpConfig(
            company_id=user.company_id,
            host=body.host,
            port=body.port,
            username=body.username,
            password_encrypted=_enc(body.password),
            from_name=body.from_name,
            from_email=body.from_email,
            use_tls=body.use_tls,
            is_verified=False,
            created_at=now,
            updated_at=now,
        )
        db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    out = SmtpConfigOut.model_validate(cfg)
    return ApiResponse(success=True, data={**out.model_dump(), "password": "••••••••"}, message="SMTP config saved")


@router.post("/email/smtp-config/test")
async def test_smtp_config(db: DBSession, user: AuthUser):
    user.require("crm.edit")
    cfg = await _get_smtp_config(user.company_id, db)
    if not cfg:
        raise HTTPException(400, "SMTP not configured")

    try:
        password = _dec(cfg.password_encrypted)
        msg = MIMEText("This is a test email from your CRM system.", "plain")
        msg["Subject"] = "CRM SMTP Test"
        msg["From"] = f"{cfg.from_name} <{cfg.from_email}>" if cfg.from_name else cfg.from_email
        msg["To"] = cfg.from_email

        await aiosmtplib.send(msg, **_smtp_transport_kwargs(cfg, password))
        cfg.is_verified = True
        cfg.updated_at = _now()
        await db.commit()
        return ApiResponse(success=True, message="Test email sent successfully")
    except Exception as e:
        logger.error("SMTP test failed: %s", e)
        raise HTTPException(400, f"SMTP test failed: {e}") from e


# ── Emails ────────────────────────────────────────────────────────────────────

@router.get("/emails")
async def list_emails(
    db: DBSession, user: AuthUser,
    lead_id: UUID | None = None,
    person_id: UUID | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("crm.view")
    filters = [CrmEmail.company_id == user.company_id]
    if lead_id:
        filters.append(CrmEmail.lead_id == lead_id)
    if person_id:
        filters.append(CrmEmail.person_id == person_id)

    total_result = await db.execute(select(func.count(CrmEmail.id)).where(*filters))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CrmEmail)
        .where(*filters)
        .order_by(CrmEmail.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    emails = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[EmailListOut.model_validate(e) for e in emails],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/emails", status_code=201)
async def send_email(body: EmailCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")

    cfg = await _get_smtp_config(user.company_id, db)
    if not cfg:
        raise HTTPException(400, "SMTP not configured")

    from_address = f"{cfg.from_name} <{cfg.from_email}>" if cfg.from_name else cfg.from_email
    now = _now()

    # Save as draft first
    email_record = CrmEmail(
        company_id=user.company_id,
        direction="out",
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        from_address=from_address,
        to_addresses=body.to_addresses,
        cc_addresses=body.cc_addresses,
        bcc_addresses=body.bcc_addresses,
        status="draft",
        in_reply_to=body.in_reply_to,
        lead_id=body.lead_id,
        person_id=body.person_id,
        quote_id=body.quote_id,
        created_by=user.user_id,
        created_at=now,
    )
    db.add(email_record)
    await db.flush()

    # Attempt to send
    try:
        password = _dec(cfg.password_encrypted)

        if body.body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body.body_text, "plain"))
            msg.attach(MIMEText(body.body_html, "html"))
        else:
            msg = MIMEText(body.body_text, "plain")

        msg["Subject"] = body.subject
        msg["From"] = from_address
        msg["To"] = ", ".join(body.to_addresses)
        if body.cc_addresses:
            msg["Cc"] = ", ".join(body.cc_addresses)
        if body.in_reply_to:
            msg["In-Reply-To"] = body.in_reply_to

        all_recipients = body.to_addresses + body.cc_addresses + body.bcc_addresses

        await aiosmtplib.send(
            msg,
            recipients=all_recipients,
            **_smtp_transport_kwargs(cfg, password),
        )

        email_record.status = "sent"
        email_record.sent_at = _now()
    except Exception as e:
        logger.error("Email send failed: %s", e)
        email_record.status = "failed"
        email_record.error_message = str(e)

    await db.commit()
    await db.refresh(email_record)
    return ApiResponse(success=True, data=EmailOut.model_validate(email_record))


@router.get("/emails/{email_id}")
async def get_email(email_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmEmail).where(CrmEmail.id == email_id, CrmEmail.company_id == user.company_id)
    )
    email_record = result.scalar_one_or_none()
    if not email_record:
        raise HTTPException(404, "Email not found")
    return ApiResponse(success=True, data=EmailOut.model_validate(email_record))


# ── Email Templates (Phase 4) ─────────────────────────────────────────────────

@router.get("/email-templates")
async def list_email_templates(
    db: DBSession, user: AuthUser, category: str | None = None,
):
    user.require("crm.view")
    q = select(CrmEmailTemplate).where(
        CrmEmailTemplate.company_id == user.company_id,
        CrmEmailTemplate.is_active.is_(True),
    )
    if category:
        q = q.where(CrmEmailTemplate.category == category)
    result = await db.execute(q.order_by(CrmEmailTemplate.name))
    return ApiResponse(success=True, data=[EmailTemplateOut.model_validate(t) for t in result.scalars().all()])


@router.post("/email-templates", status_code=201)
async def create_email_template(body: EmailTemplateCreate, db: DBSession, user: AuthUser):
    user.require("crm.create")
    now = _now()
    tmpl = CrmEmailTemplate(
        company_id=user.company_id,
        name=body.name,
        subject=body.subject,
        body_text=body.body_text,
        body_html=body.body_html,
        category=body.category,
        created_by=user.user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return ApiResponse(success=True, data=EmailTemplateOut.model_validate(tmpl), message="Email template created")


@router.patch("/email-templates/{template_id}")
async def update_email_template(template_id: UUID, body: EmailTemplateUpdate, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmEmailTemplate).where(
            CrmEmailTemplate.id == template_id,
            CrmEmailTemplate.company_id == user.company_id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(404, "Email template not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, val)
    tmpl.updated_at = _now()
    await db.commit()
    await db.refresh(tmpl)
    return ApiResponse(success=True, data=EmailTemplateOut.model_validate(tmpl))


@router.delete("/email-templates/{template_id}", status_code=200)
async def delete_email_template(template_id: UUID, db: DBSession, user: AuthUser):
    user.require("crm.edit")
    result = await db.execute(
        select(CrmEmailTemplate).where(
            CrmEmailTemplate.id == template_id,
            CrmEmailTemplate.company_id == user.company_id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(404, "Email template not found")
    tmpl.is_active = False
    tmpl.updated_at = _now()
    await db.commit()
    return ApiResponse(success=True, message="Email template deleted")


# ── CSV Lead Import (Phase 4) ─────────────────────────────────────────────────

def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return Decimal("0")


@router.post("/leads/import", status_code=201)
async def import_leads_csv(
    db: DBSession,
    user: AuthUser,
    file: UploadFile,
    pipeline_id: str = Form(...),
    stage_id: str = Form(...),
    assigned_to: str | None = Form(default=None),
):
    user.require("crm.create")

    # Validate file type
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(400, "File must be a CSV (.csv extension required)")

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text_content = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    # Normalize headers to lowercase
    raw_rows = list(reader)
    if len(raw_rows) > 1000:
        raise HTTPException(400, "CSV exceeds 1000-row limit")

    # Normalize row keys to lowercase
    rows = [{k.lower().strip(): v for k, v in row.items()} for row in raw_rows]

    try:
        p_id = UUID(pipeline_id)
        s_id = UUID(stage_id)
        a_id = UUID(assigned_to) if assigned_to else None
    except ValueError as exc:
        raise HTTPException(400, f"Invalid UUID in form fields: {exc}") from exc

    now = _now()
    imported = 0
    errors: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        title = row.get("title", "").strip()
        if not title:
            errors.append({"row": idx, "error": "Missing required field: title"})
            continue
        try:
            lead = CrmLead(
                company_id=user.company_id,
                title=title,
                description=row.get("description", "").strip() or None,
                lead_value=_parse_decimal(row.get("lead_value", "0")),
                expected_close_date=_parse_date(row.get("expected_close_date", "")),
                pipeline_id=p_id,
                stage_id=s_id,
                assigned_to=a_id,
                status="open",
                created_by=user.user_id,
                created_at=now,
                updated_at=now,
            )
            db.add(lead)
            imported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "error": str(exc)})

    import_record = CrmLeadImport(
        company_id=user.company_id,
        filename=filename,
        total_rows=len(rows),
        imported_rows=imported,
        failed_rows=len(errors),
        status="done",
        errors=errors,
        pipeline_id=p_id,
        stage_id=s_id,
        assigned_to=a_id,
        created_by=user.user_id,
        created_at=now,
        completed_at=_now(),
    )
    db.add(import_record)
    await db.commit()
    await db.refresh(import_record)
    return ApiResponse(success=True, data=LeadImportOut.model_validate(import_record))


@router.get("/leads/import/history")
async def list_import_history(db: DBSession, user: AuthUser):
    user.require("crm.view")
    result = await db.execute(
        select(CrmLeadImport)
        .where(CrmLeadImport.company_id == user.company_id)
        .order_by(CrmLeadImport.created_at.desc())
        .limit(100)
    )
    return ApiResponse(success=True, data=[LeadImportOut.model_validate(r) for r in result.scalars().all()])


# ── Bulk Actions (Phase 4) ────────────────────────────────────────────────────

@router.post("/leads/bulk-action")
async def bulk_action_leads(body: LeadBulkActionIn, db: DBSession, user: AuthUser):
    user.require("crm.edit")

    if len(body.lead_ids) > 500:
        raise HTTPException(400, "Cannot process more than 500 leads at once")

    if body.action not in {"assign", "stage", "tag", "archive"}:
        raise HTTPException(400, "action must be one of: assign, stage, tag, archive")

    # Fetch leads belonging to this company only
    result = await db.execute(
        select(CrmLead).where(
            CrmLead.id.in_(body.lead_ids),
            CrmLead.company_id == user.company_id,
        )
    )
    leads = result.scalars().all()
    count = len(leads)

    if body.action == "assign":
        if not body.value:
            raise HTTPException(400, "value (user UUID) required for action=assign")
        try:
            assignee_id = UUID(body.value)
        except ValueError as exc:
            raise HTTPException(400, f"Invalid UUID for assign: {exc}") from exc
        by_name_map = await _resolve_user_names(db, user.company_id, {user.user_id})
        for lead in leads:
            await _assign_lead(db, lead, assignee_id, user.user_id, by_name_map.get(user.user_id))

    elif body.action == "stage":
        if not body.value:
            raise HTTPException(400, "value (stage UUID) required for action=stage")
        try:
            stage_uuid = UUID(body.value)
        except ValueError as exc:
            raise HTTPException(400, f"Invalid UUID for stage: {exc}") from exc
        for lead in leads:
            lead.stage_id = stage_uuid
            lead.updated_at = _now()

    elif body.action == "tag":
        if not body.value:
            raise HTTPException(400, "value (tag name) required for action=tag")
        tag_name = body.value.strip()
        # Find or create the tag
        tag_result = await db.execute(
            select(CrmTag).where(
                CrmTag.company_id == user.company_id,
                CrmTag.name == tag_name,
            )
        )
        tag = tag_result.scalar_one_or_none()
        if not tag:
            tag = CrmTag(
                company_id=user.company_id,
                name=tag_name,
                created_at=_now(),
            )
            db.add(tag)
            await db.flush()

        # Add tag to each lead (skip if already tagged)
        existing_result = await db.execute(
            select(CrmLeadTag.lead_id).where(
                CrmLeadTag.tag_id == tag.id,
                CrmLeadTag.lead_id.in_([lead.id for lead in leads]),
            )
        )
        already_tagged = {row for row in existing_result.scalars().all()}
        for lead in leads:
            if lead.id not in already_tagged:
                db.add(CrmLeadTag(lead_id=lead.id, tag_id=tag.id))

    elif body.action == "archive":
        now = _now()
        for lead in leads:
            lead.status = "lost"
            lead.closed_at = now
            lead.updated_at = now

    await db.commit()
    return ApiResponse(success=True, data={"affected": count})


# ── CRM Reports (Phase 4) ─────────────────────────────────────────────────────

def _apply_date_filters(q, date_from: date | None, date_to: date | None):
    if date_from:
        q = q.where(CrmLead.created_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        q = q.where(CrmLead.created_at < datetime(date_to.year, date_to.month, date_to.day + 1, tzinfo=timezone.utc))
    return q


@router.get("/reports/pipeline")
async def report_pipeline(
    db: DBSession, user: AuthUser,
    date_from: date | None = None, date_to: date | None = None,
):
    user.require("crm.view")
    q = (
        select(
            CrmPipelineStage.id.label("stage_id"),
            CrmPipelineStage.name.label("stage_name"),
            CrmPipelineStage.sort_order,
            CrmPipelineStage.is_won,
            CrmPipelineStage.is_lost,
            func.count(CrmLead.id).label("lead_count"),
            func.coalesce(func.sum(CrmLead.lead_value), Decimal("0")).label("total_value"),
        )
        .join(CrmPipeline, CrmPipeline.id == CrmPipelineStage.pipeline_id)
        .outerjoin(
            CrmLead,
            and_(
                CrmLead.stage_id == CrmPipelineStage.id,
                CrmLead.company_id == user.company_id,
            ),
        )
        .where(CrmPipeline.company_id == user.company_id)
        .group_by(
            CrmPipelineStage.id, CrmPipelineStage.name,
            CrmPipelineStage.sort_order, CrmPipelineStage.is_won, CrmPipelineStage.is_lost,
        )
        .order_by(CrmPipelineStage.sort_order)
    )
    result = await db.execute(q)
    return ApiResponse(success=True, data=[
        {
            "stage_id": str(row.stage_id),
            "stage_name": row.stage_name,
            "sort_order": row.sort_order,
            "is_won": row.is_won,
            "is_lost": row.is_lost,
            "lead_count": row.lead_count,
            "total_value": float(row.total_value),
        }
        for row in result
    ])


@router.get("/reports/sources")
async def report_sources(
    db: DBSession, user: AuthUser,
    date_from: date | None = None, date_to: date | None = None,
):
    user.require("crm.view")
    q = (
        select(
            CrmLeadSource.id.label("source_id"),
            CrmLeadSource.name.label("source_name"),
            func.count(CrmLead.id).label("count"),
            func.coalesce(func.sum(CrmLead.lead_value), Decimal("0")).label("total_value"),
            func.count(CrmLead.id).filter(CrmLead.status == "won").label("won_count"),
        )
        .outerjoin(CrmLead, and_(
            CrmLead.source_id == CrmLeadSource.id,
            CrmLead.company_id == user.company_id,
        ))
        .where(CrmLeadSource.company_id == user.company_id)
        .group_by(CrmLeadSource.id, CrmLeadSource.name)
        .order_by(func.count(CrmLead.id).desc())
    )
    result = await db.execute(q)
    return ApiResponse(success=True, data=[
        {
            "source_id": str(row.source_id),
            "source_name": row.source_name,
            "count": row.count,
            "total_value": float(row.total_value),
            "won_count": row.won_count,
        }
        for row in result
    ])


@router.get("/reports/activities")
async def report_activities(
    db: DBSession, user: AuthUser,
    date_from: date | None = None, date_to: date | None = None,
):
    user.require("crm.view")
    q = (
        select(
            CrmActivity.type,
            func.count(CrmActivity.id).label("count"),
            func.count(CrmActivity.id).filter(CrmActivity.is_done.is_(True)).label("done_count"),
        )
        .where(CrmActivity.company_id == user.company_id)
        .group_by(CrmActivity.type)
        .order_by(CrmActivity.type)
    )
    result = await db.execute(q)
    rows = []
    for row in result:
        completion_rate = round(row.done_count / row.count * 100, 1) if row.count > 0 else 0.0
        rows.append({
            "type": row.type,
            "count": row.count,
            "done_count": row.done_count,
            "completion_rate": completion_rate,
        })
    return ApiResponse(success=True, data=rows)


@router.get("/reports/quotes")
async def report_quotes(
    db: DBSession, user: AuthUser,
    date_from: date | None = None, date_to: date | None = None,
):
    user.require("crm.view")
    q = (
        select(
            CrmQuote.status,
            func.count(CrmQuote.id).label("count"),
            func.coalesce(func.sum(CrmQuote.total_amount), Decimal("0")).label("total_value"),
        )
        .where(CrmQuote.company_id == user.company_id)
        .group_by(CrmQuote.status)
    )
    if date_from:
        q = q.where(CrmQuote.created_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        q = q.where(CrmQuote.created_at < datetime(date_to.year, date_to.month, date_to.day + 1, tzinfo=timezone.utc))

    result = await db.execute(q)
    by_status: dict[str, dict] = {
        s: {"count": 0, "total_value": Decimal("0")}
        for s in ("draft", "sent", "accepted", "declined", "expired")
    }
    for row in result:
        if row.status in by_status:
            by_status[row.status]["count"] = row.count
            by_status[row.status]["total_value"] = row.total_value

    sent_like = ("sent", "accepted", "declined", "expired")
    return ApiResponse(success=True, data={
        **{s: by_status[s]["count"] for s in by_status},
        "accepted_value": float(by_status["accepted"]["total_value"]),
        "total_sent_value": float(sum((by_status[s]["total_value"] for s in sent_like), Decimal("0"))),
    })


@router.get("/reports/monthly-trend")
async def report_monthly_trend(
    db: DBSession, user: AuthUser,
    date_from: date | None = None, date_to: date | None = None,
):
    user.require("crm.view")
    # Group/order by the "month" label rather than repeating the date_trunc(...)
    # expression — each repeated call binds "month" as a separate parameter,
    # which Postgres can't statically prove is identical to the SELECT-list
    # expression, and rejects with "must appear in the GROUP BY clause".
    month_col = func.date_trunc("month", CrmLead.created_at).label("month")
    q = (
        select(
            month_col,
            func.count().label("count"),
            func.coalesce(func.sum(CrmLead.lead_value), 0).label("value"),
        )
        .where(CrmLead.company_id == user.company_id)
        .group_by(literal_column('"month"'))
        .order_by(literal_column('"month"').asc())
        .limit(12)
    )
    if date_from:
        q = q.where(CrmLead.created_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc))
    if date_to:
        q = q.where(CrmLead.created_at < datetime(date_to.year, date_to.month, date_to.day + 1, tzinfo=timezone.utc))

    result = await db.execute(q)
    return ApiResponse(success=True, data=[
        {
            "month": row.month.strftime("%Y-%m") if row.month else None,
            "count": row.count,
            "value": float(row.value),
        }
        for row in result
    ])


# ── Lead Intelligence: scoring configuration (admin) ───────────────────────────

@router.get("/scoring-rules")
async def list_scoring_rules(db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rules = (await db.execute(
        select(CrmLeadScoringRule).where(CrmLeadScoringRule.company_id == user.company_id)
        .order_by(CrmLeadScoringRule.category, CrmLeadScoringRule.code)
    )).scalars().all()
    return ApiResponse(success=True, data=[ScoringRuleOut.model_validate(r) for r in rules])


@router.patch("/scoring-rules/{rule_id}")
async def update_scoring_rule(rule_id: UUID, body: ScoringRuleUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rule = (await db.execute(
        select(CrmLeadScoringRule).where(CrmLeadScoringRule.id == rule_id, CrmLeadScoringRule.company_id == user.company_id)
    )).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Scoring rule not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, val)
    rule.updated_at = _now()
    await db.commit()
    return ApiResponse(success=True, data=ScoringRuleOut.model_validate(rule), message="Scoring rule updated")


@router.get("/scoring-thresholds")
async def get_scoring_thresholds(db: DBSession, user: AuthUser):
    user.require("crm.view")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    return ApiResponse(success=True, data=ScoringThresholdsOut(
        lead_score_high_threshold=company.lead_score_high_threshold,
        lead_score_medium_threshold=company.lead_score_medium_threshold,
    ))


@router.put("/scoring-thresholds")
async def update_scoring_thresholds(body: ScoringThresholdsUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    data = body.model_dump(exclude_none=True)
    high = data.get("lead_score_high_threshold", company.lead_score_high_threshold)
    medium = data.get("lead_score_medium_threshold", company.lead_score_medium_threshold)
    if medium >= high:
        raise HTTPException(422, "Medium threshold must be lower than the high threshold")
    for field, val in data.items():
        setattr(company, field, val)
    await db.commit()
    return ApiResponse(success=True, data=ScoringThresholdsOut(
        lead_score_high_threshold=company.lead_score_high_threshold,
        lead_score_medium_threshold=company.lead_score_medium_threshold,
    ), message="Thresholds updated")


@router.get("/service-areas")
async def list_service_areas(db: DBSession, user: AuthUser):
    user.require("crm.view")
    areas = (await db.execute(
        select(CrmLeadServiceArea).where(CrmLeadServiceArea.company_id == user.company_id)
        .order_by(CrmLeadServiceArea.tier, CrmLeadServiceArea.location_name)
    )).scalars().all()
    return ApiResponse(success=True, data=[ServiceAreaOut.model_validate(a) for a in areas])


@router.post("/service-areas", status_code=201)
async def create_service_area(body: ServiceAreaCreate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    if body.tier not in ("preferred", "secondary", "non_serviceable"):
        raise HTTPException(422, "tier must be one of: preferred, secondary, non_serviceable")
    area = CrmLeadServiceArea(
        company_id=user.company_id, location_name=body.location_name, tier=body.tier, created_at=_now(),
    )
    db.add(area)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "This location is already configured") from None
    return ApiResponse(success=True, data=ServiceAreaOut.model_validate(area), message="Service area added")


@router.patch("/service-areas/{area_id}")
async def update_service_area(area_id: UUID, body: ServiceAreaUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    area = (await db.execute(
        select(CrmLeadServiceArea).where(CrmLeadServiceArea.id == area_id, CrmLeadServiceArea.company_id == user.company_id)
    )).scalar_one_or_none()
    if not area:
        raise HTTPException(404, "Service area not found")
    data = body.model_dump(exclude_unset=True)
    if "tier" in data and data["tier"] not in ("preferred", "secondary", "non_serviceable"):
        raise HTTPException(422, "tier must be one of: preferred, secondary, non_serviceable")
    for field, val in data.items():
        setattr(area, field, val)
    await db.commit()
    return ApiResponse(success=True, data=ServiceAreaOut.model_validate(area), message="Service area updated")


@router.delete("/service-areas/{area_id}")
async def delete_service_area(area_id: UUID, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    area = (await db.execute(
        select(CrmLeadServiceArea).where(CrmLeadServiceArea.id == area_id, CrmLeadServiceArea.company_id == user.company_id)
    )).scalar_one_or_none()
    if not area:
        raise HTTPException(404, "Service area not found")
    await db.delete(area)
    await db.commit()
    return ApiResponse(success=True, message="Service area deleted")


# ── Lead Assignment configuration (admin) ───────────────────────────────────────

@router.get("/assignment-rules")
async def list_assignment_rules(db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rules = (await db.execute(
        select(CrmLeadAssignmentRule).where(CrmLeadAssignmentRule.company_id == user.company_id)
        .order_by(CrmLeadAssignmentRule.sort_order)
    )).scalars().all()
    name_map = await _resolve_user_names(db, user.company_id, {r.assign_to for r in rules})
    return ApiResponse(success=True, data=[
        AssignmentRuleOut(
            id=r.id, name=r.name, sort_order=r.sort_order, is_active=r.is_active,
            source_id=r.source_id, min_score=r.min_score, location_tier=r.location_tier,
            assign_to=r.assign_to, assign_to_name=name_map.get(r.assign_to),
        ) for r in rules
    ])


@router.post("/assignment-rules", status_code=201)
async def create_assignment_rule(body: AssignmentRuleCreate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rule = CrmLeadAssignmentRule(
        company_id=user.company_id, name=body.name, sort_order=body.sort_order, is_active=body.is_active,
        source_id=body.source_id, min_score=body.min_score, location_tier=body.location_tier,
        assign_to=body.assign_to, created_at=_now(), updated_at=_now(),
    )
    db.add(rule)
    await db.commit()
    return ApiResponse(success=True, data=AssignmentRuleOut.model_validate(rule), message="Assignment rule created")


@router.patch("/assignment-rules/{rule_id}")
async def update_assignment_rule(rule_id: UUID, body: AssignmentRuleUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rule = (await db.execute(
        select(CrmLeadAssignmentRule).where(CrmLeadAssignmentRule.id == rule_id, CrmLeadAssignmentRule.company_id == user.company_id)
    )).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Assignment rule not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, val)
    rule.updated_at = _now()
    await db.commit()
    return ApiResponse(success=True, data=AssignmentRuleOut.model_validate(rule), message="Assignment rule updated")


@router.delete("/assignment-rules/{rule_id}")
async def delete_assignment_rule(rule_id: UUID, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    rule = (await db.execute(
        select(CrmLeadAssignmentRule).where(CrmLeadAssignmentRule.id == rule_id, CrmLeadAssignmentRule.company_id == user.company_id)
    )).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Assignment rule not found")
    await db.delete(rule)
    await db.commit()
    return ApiResponse(success=True, message="Assignment rule deleted")


@router.get("/assignment-pool")
async def list_assignment_pool(db: DBSession, user: AuthUser):
    user.require("admin.settings")
    members = (await db.execute(
        select(CrmLeadAssignmentPool).where(CrmLeadAssignmentPool.company_id == user.company_id)
        .order_by(CrmLeadAssignmentPool.sort_order)
    )).scalars().all()
    name_map = await _resolve_user_names(db, user.company_id, {m.user_id for m in members})
    return ApiResponse(success=True, data=[
        AssignmentPoolMemberOut(
            id=m.id, user_id=m.user_id, user_name=name_map.get(m.user_id),
            sort_order=m.sort_order, is_active=m.is_active,
        ) for m in members
    ])


@router.post("/assignment-pool", status_code=201)
async def add_assignment_pool_member(body: AssignmentPoolMemberIn, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    member = CrmLeadAssignmentPool(
        company_id=user.company_id, user_id=body.user_id, sort_order=body.sort_order, created_at=_now(),
    )
    db.add(member)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "This employee is already in the round-robin pool") from None
    return ApiResponse(success=True, data=AssignmentPoolMemberOut.model_validate(member), message="Added to assignment pool")


@router.patch("/assignment-pool/{member_id}")
async def update_assignment_pool_member(member_id: UUID, body: dict, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    member = (await db.execute(
        select(CrmLeadAssignmentPool).where(CrmLeadAssignmentPool.id == member_id, CrmLeadAssignmentPool.company_id == user.company_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Pool member not found")
    if "is_active" in body:
        member.is_active = bool(body["is_active"])
    if "sort_order" in body:
        member.sort_order = int(body["sort_order"])
    await db.commit()
    return ApiResponse(success=True, data=AssignmentPoolMemberOut.model_validate(member), message="Pool member updated")


@router.delete("/assignment-pool/{member_id}")
async def remove_assignment_pool_member(member_id: UUID, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    member = (await db.execute(
        select(CrmLeadAssignmentPool).where(CrmLeadAssignmentPool.id == member_id, CrmLeadAssignmentPool.company_id == user.company_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Pool member not found")
    await db.delete(member)
    await db.commit()
    return ApiResponse(success=True, message="Removed from assignment pool")


@router.get("/response-targets")
async def get_response_targets(db: DBSession, user: AuthUser):
    user.require("crm.view")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    return ApiResponse(success=True, data=ResponseTargetsOut.model_validate(company))


@router.put("/response-targets")
async def update_response_targets(body: ResponseTargetsUpdate, db: DBSession, user: AuthUser):
    user.require("admin.settings")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(company, field, val)
    await db.commit()
    return ApiResponse(success=True, data=ResponseTargetsOut.model_validate(company), message="Response targets updated")


@router.get("/reports/response-time")
async def response_time_report(db: DBSession, user: AuthUser):
    """Average/median time-to-assignment and time-to-first-response, by
    employee and overall (spec Step 9). Only counts leads that actually
    have the relevant timestamps - an unassigned or never-contacted lead
    simply isn't included in that average, rather than being counted as 0."""
    user.require("reports.view")
    rows = (await db.execute(
        select(CrmLead.assigned_to, CrmLead.created_at, CrmLead.assigned_date, CrmLead.first_contacted_at, CrmLead.priority)
        .where(CrmLead.company_id == user.company_id)
    )).all()

    def minutes(a, b):
        if not a or not b or b < a:
            return None
        return (b - a).total_seconds() / 60

    assign_times = [m for m in (minutes(r.created_at, r.assigned_date) for r in rows) if m is not None]
    response_times = [m for m in (minutes(r.created_at, r.first_contacted_at) for r in rows) if m is not None]
    high_response_times = [
        m for r in rows if r.priority == "high"
        for m in [minutes(r.created_at, r.first_contacted_at)] if m is not None
    ]

    by_employee: dict[UUID, list[float]] = {}
    for r in rows:
        if r.assigned_to and r.first_contacted_at:
            m = minutes(r.created_at, r.first_contacted_at)
            if m is not None:
                by_employee.setdefault(r.assigned_to, []).append(m)
    name_map = await _resolve_user_names(db, user.company_id, set(by_employee.keys()))

    def summarize(values: list[float]) -> dict:
        if not values:
            return {"count": 0, "avg_minutes": None, "median_minutes": None}
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        median = sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return {"count": len(values), "avg_minutes": round(sum(values) / len(values), 1), "median_minutes": round(median, 1)}

    return ApiResponse(success=True, data={
        "time_to_assignment": summarize(assign_times),
        "time_to_first_response": summarize(response_times),
        "time_to_first_response_high_priority": summarize(high_response_times),
        "by_employee": [
            {"user_id": str(uid), "user_name": name_map.get(uid), **summarize(values)}
            for uid, values in by_employee.items()
        ],
    })


# ── Predictive Scoring: data-sufficiency gate (Phase 3, Step 1) ────────────────
# No model, feature store, or training pipeline exists - the data audit
# (docs/PREDICTIVE_SCORING_DATA_AUDIT.md) found the real company has 9
# total leads, 1 won, 1 lost. This endpoint is the one piece of real
# infrastructure that audit calls for: an honest, live check against
# configurable thresholds, so the system can say "not ready" with real
# numbers rather than ever fabricating a prediction. See spec Phase 30.

@router.get("/predictive-scoring/readiness")
async def predictive_scoring_readiness(db: DBSession, user: AuthUser):
    user.require("crm.view")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")

    total = (await db.execute(
        select(func.count(CrmLead.id)).where(CrmLead.company_id == user.company_id)
    )).scalar() or 0
    # "Converted" uses lead status today, not sales_order_id — the audit found
    # sales_order_id is unset on every existing lead, so it can't be used as
    # the conversion signal yet. Documented in the audit as a gap to close.
    converted = (await db.execute(
        select(func.count(CrmLead.id)).where(CrmLead.company_id == user.company_id, CrmLead.status == "won")
    )).scalar() or 0
    not_converted = (await db.execute(
        select(func.count(CrmLead.id)).where(CrmLead.company_id == user.company_id, CrmLead.status == "lost")
    )).scalar() or 0

    ready = (
        total >= company.predictive_scoring_min_leads
        and converted >= company.predictive_scoring_min_outcomes_per_class
        and not_converted >= company.predictive_scoring_min_outcomes_per_class
    )
    gaps = []
    if total < company.predictive_scoring_min_leads:
        gaps.append(f"{total} of {company.predictive_scoring_min_leads} leads needed overall")
    if converted < company.predictive_scoring_min_outcomes_per_class:
        gaps.append(f"{converted} of {company.predictive_scoring_min_outcomes_per_class} converted outcomes")
    if not_converted < company.predictive_scoring_min_outcomes_per_class:
        gaps.append(f"{not_converted} of {company.predictive_scoring_min_outcomes_per_class} non-converted outcomes")
    reason = "Sufficient historical data." if ready else "Predictive scoring unavailable: insufficient historical data — " + "; ".join(gaps)

    return ApiResponse(success=True, data=PredictiveScoringReadinessOut(
        ready=ready, leads_total=total, leads_total_required=company.predictive_scoring_min_leads,
        converted=converted, not_converted=not_converted,
        outcomes_required_per_class=company.predictive_scoring_min_outcomes_per_class,
        reason=reason, checked_at=_now(),
    ))
