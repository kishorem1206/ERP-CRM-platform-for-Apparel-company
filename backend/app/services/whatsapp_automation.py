"""Dispatches configurable WhatsApp automation rules at CRM trigger points.

Never calls the Meta API directly - each message is written as a `queued`
WhatsappAutomationLog row and sent later by
app.workers.jobs.send_due_whatsapp_automations (on the cron tick once the
rule's delay has passed, or within seconds for zero-delay rules), so a
slow/unconfigured WhatsApp integration can never block or fail the CRM action
that triggered it.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.crm import CrmLead, CrmPerson
from app.models.sales import Customer
from app.models.user import User
from app.models.whatsapp import WhatsappAutomationLog, WhatsappAutomationRule

logger = logging.getLogger(__name__)


async def _resolve_phones(
    db: AsyncSession, lead: CrmLead, recipient_type: str
) -> list[tuple[str, Optional[str]]]:
    """Returns [(phone, recipient_type), ...] for the rule's recipient_type.
    Every source field is nullable; callers must handle an empty result."""
    results: list[tuple[str, Optional[str]]] = []

    if recipient_type in ("customer", "both"):
        phone = None
        if lead.person_id:
            person = (await db.execute(select(CrmPerson).where(CrmPerson.id == lead.person_id))).scalar_one_or_none()
            if person:
                phone = person.whatsapp_number or (person.contact_numbers[0] if person.contact_numbers else None)
        if not phone and lead.customer_id:
            customer = (await db.execute(select(Customer).where(Customer.id == lead.customer_id))).scalar_one_or_none()
            if customer:
                phone = customer.whatsapp_no or customer.mobile
        if phone:
            results.append((phone, "customer"))

    if recipient_type in ("employee", "both"):
        if lead.assigned_to:
            user = (await db.execute(select(User).where(User.id == lead.assigned_to))).scalar_one_or_none()
            if user and user.phone:
                results.append((user.phone, "employee"))

    return results


async def resolve_customer_name(db: AsyncSession, lead: CrmLead) -> str:
    """Best-effort display name for a lead's customer, for {{customer_name}}."""
    if lead.person_id:
        person = (await db.execute(select(CrmPerson).where(CrmPerson.id == lead.person_id))).scalar_one_or_none()
        if person:
            return person.name
    if lead.customer_id:
        customer = (await db.execute(select(Customer).where(Customer.id == lead.customer_id))).scalar_one_or_none()
        if customer:
            return customer.trade_name or customer.legal_name
    return "Customer"


async def resolve_company_name(db: AsyncSession, company_id: UUID) -> str:
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    return company.name if company else ""


async def fire_event(
    db: AsyncSession,
    company_id: UUID,
    trigger_event: str,
    context: dict[str, str],
    lead: Optional[CrmLead] = None,
) -> None:
    """Queue configured WhatsApp automation rules for a trigger event. Never
    raises - an automation failure must not break the primary CRM action."""
    send_now = False
    try:
        rules = (
            await db.execute(
                select(WhatsappAutomationRule).where(
                    WhatsappAutomationRule.company_id == company_id,
                    WhatsappAutomationRule.trigger_event == trigger_event,
                    WhatsappAutomationRule.is_active.is_(True),
                )
            )
        ).scalars().all()
        if not rules:
            return

        for rule in rules:
            phones = await _resolve_phones(db, lead, rule.recipient_type) if lead else []
            if not phones:
                db.add(
                    WhatsappAutomationLog(
                        rule_id=rule.id,
                        lead_id=lead.id if lead else None,
                        recipient_phone=None,
                        rendered_body=None,
                        status="skipped_no_phone",
                    )
                )
                continue

            from app.services.template_render import render

            body_template = rule.message_body or ""
            rendered = render(body_template, context) if body_template else ""

            for phone, _recipient_label in phones:
                log = WhatsappAutomationLog(
                    rule_id=rule.id,
                    lead_id=lead.id if lead else None,
                    recipient_phone=phone,
                    rendered_body=rendered,
                    status="queued",
                )
                db.add(log)
                await db.flush()
                if rule.delay_minutes == 0:
                    send_now = True
        if send_now:
            _send_soon()
    except Exception:
        logger.warning("whatsapp_automation.fire_event failed for trigger=%s", trigger_event, exc_info=True)


# Strong references to in-flight sends — asyncio only keeps weak ones, so an
# unreferenced task can be garbage-collected mid-flight.
_pending_sends: set = set()


def _send_soon(delay_seconds: float = 5.0) -> None:
    """Send zero-delay messages shortly after the triggering request commits,
    instead of waiting for the next cron tick. The log rows are written in
    the caller's transaction, which commits only after the request returns,
    so this waits a few seconds first; anything not yet committed by then is
    simply picked up by the next tick."""
    import asyncio

    from app.workers.jobs import send_due_whatsapp_automations

    async def _run() -> None:
        await asyncio.sleep(delay_seconds)
        try:
            await send_due_whatsapp_automations()
        except Exception:
            logger.warning("Immediate WhatsApp automation send failed; the cron tick will retry", exc_info=True)

    try:
        task = asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        return  # no running loop - the cron tick will send it
    _pending_sends.add(task)
    task.add_done_callback(_pending_sends.discard)
