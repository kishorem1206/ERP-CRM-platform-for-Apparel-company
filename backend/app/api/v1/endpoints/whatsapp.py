from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, or_, select

from app.api.v1.deps import AuthUser, DBSession
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.company import Company
from app.models.whatsapp import WhatsappContact, WhatsappMessage, WhatsappTemplate
from app.schemas.base import ApiResponse, paginated
from app.schemas.whatsapp import (
    ContactOut,
    MessageOut,
    SendMessageIn,
    SendTemplateIn,
    TemplateCreate,
    TemplateOut,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_META_API = "https://graph.facebook.com/v19.0"
_PAGE_SIZE = 50


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_or_create_contact(db, company_id: UUID, phone_number: str) -> WhatsappContact:
    result = await db.execute(
        select(WhatsappContact).where(
            WhatsappContact.company_id == company_id,
            WhatsappContact.phone_number == phone_number,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        contact = WhatsappContact(company_id=company_id, phone_number=phone_number)
        db.add(contact)
        await db.flush()
    return contact


async def _call_meta(payload: dict) -> dict:
    async with httpx.AsyncClient(follow_redirects=False) as client:
        resp = await client.post(
            f"{_META_API}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Meta API error")
    return resp.json()


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return hub_challenge
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


async def _process_inbound_messages(payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as db:
        try:
            company_row = await db.execute(select(Company).limit(1))
            company = company_row.scalar_one_or_none()
            if not company:
                return

            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    my_number = metadata.get("display_phone_number", settings.WHATSAPP_PHONE_NUMBER_ID)

                    for msg in value.get("messages", []):
                        from_number = msg.get("from", "")
                        wa_message_id = msg.get("id", "")
                        msg_type = msg.get("type", "text")
                        body = msg.get("text", {}).get("body") if msg_type == "text" else None
                        ts_raw = msg.get("timestamp")
                        wa_ts = (
                            datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
                            if ts_raw
                            else None
                        )

                        contact = await _get_or_create_contact(db, company.id, from_number)

                        db.add(
                            WhatsappMessage(
                                company_id=company.id,
                                wa_message_id=wa_message_id,
                                direction="inbound",
                                from_number=from_number,
                                to_number=my_number,
                                message_type=msg_type,
                                body=body,
                                status="received",
                                wa_timestamp=wa_ts,
                                contact_id=contact.id,
                            )
                        )

            await db.commit()
        except Exception:
            await db.rollback()


@router.post("/webhook", status_code=200)
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(_process_inbound_messages, payload)
    return {"status": "ok"}


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.get("/contacts")
async def list_contacts(
    user: AuthUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    search: str = Query(default=""),
):
    q = select(WhatsappContact).where(WhatsappContact.company_id == user.company_id)
    if search:
        q = q.where(
            or_(
                WhatsappContact.phone_number.ilike(f"%{search}%"),
                WhatsappContact.display_name.ilike(f"%{search}%"),
            )
        )
    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    rows = await db.execute(q.offset((page - 1) * _PAGE_SIZE).limit(_PAGE_SIZE))
    contacts = [ContactOut.model_validate(c) for c in rows.scalars()]
    return paginated(contacts, total, page, _PAGE_SIZE)


@router.get("/contacts/{contact_id}/messages")
async def contact_messages(
    contact_id: UUID,
    user: AuthUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
):
    contact_row = await db.execute(
        select(WhatsappContact).where(
            WhatsappContact.id == contact_id,
            WhatsappContact.company_id == user.company_id,
        )
    )
    if not contact_row.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    q = (
        select(WhatsappMessage)
        .where(
            WhatsappMessage.company_id == user.company_id,
            WhatsappMessage.contact_id == contact_id,
        )
        .order_by(WhatsappMessage.created_at.asc())
    )
    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    rows = await db.execute(q.offset((page - 1) * _PAGE_SIZE).limit(_PAGE_SIZE))
    messages = [MessageOut.model_validate(m) for m in rows.scalars()]
    return paginated(messages, total, page, _PAGE_SIZE)


# ── Send ──────────────────────────────────────────────────────────────────────

@router.post("/send")
async def send_message(body: SendMessageIn, user: AuthUser, db: DBSession):
    meta_payload = {
        "messaging_product": "whatsapp",
        "to": body.to_number,
        "type": "text",
        "text": {"body": body.body},
    }
    resp_data = await _call_meta(meta_payload)
    wa_message_id = (resp_data.get("messages") or [{}])[0].get("id")

    contact = await _get_or_create_contact(db, user.company_id, body.to_number)
    msg = WhatsappMessage(
        company_id=user.company_id,
        wa_message_id=wa_message_id,
        direction="outbound",
        from_number=settings.WHATSAPP_PHONE_NUMBER_ID,
        to_number=body.to_number,
        message_type="text",
        body=body.body,
        status="sent",
        contact_id=contact.id,
        created_by=user.user_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return ApiResponse(data=MessageOut.model_validate(msg))


@router.post("/send-template")
async def send_template_message(body: SendTemplateIn, user: AuthUser, db: DBSession):
    template_row = await db.execute(
        select(WhatsappTemplate).where(
            WhatsappTemplate.id == body.template_id,
            WhatsappTemplate.company_id == user.company_id,
        )
    )
    template = template_row.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    components = []
    if body.variables:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": v} for v in body.variables],
            }
        )

    meta_payload = {
        "messaging_product": "whatsapp",
        "to": body.to_number,
        "type": "template",
        "template": {
            "name": template.name,
            "language": {"code": template.language},
            "components": components,
        },
    }
    resp_data = await _call_meta(meta_payload)
    wa_message_id = (resp_data.get("messages") or [{}])[0].get("id")

    contact = await _get_or_create_contact(db, user.company_id, body.to_number)
    msg = WhatsappMessage(
        company_id=user.company_id,
        wa_message_id=wa_message_id,
        direction="outbound",
        from_number=settings.WHATSAPP_PHONE_NUMBER_ID,
        to_number=body.to_number,
        message_type="template",
        body=template.body_text,
        status="sent",
        contact_id=contact.id,
        created_by=user.user_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return ApiResponse(data=MessageOut.model_validate(msg))


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(user: AuthUser, db: DBSession):
    rows = await db.execute(
        select(WhatsappTemplate).where(WhatsappTemplate.company_id == user.company_id)
    )
    templates = [TemplateOut.model_validate(t) for t in rows.scalars()]
    return ApiResponse(data=templates)


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateCreate, user: AuthUser, db: DBSession):
    template = WhatsappTemplate(company_id=user.company_id, **body.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return ApiResponse(data=TemplateOut.model_validate(template))
