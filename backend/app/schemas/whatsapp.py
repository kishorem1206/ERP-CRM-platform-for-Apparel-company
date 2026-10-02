from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ContactOut(BaseModel):
    id: UUID
    company_id: UUID
    phone_number: str
    display_name: Optional[str] = None
    person_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ContactListOut(BaseModel):
    contacts: list[ContactOut]
    total: int


class MessageOut(BaseModel):
    id: UUID
    wa_message_id: Optional[str] = None
    direction: str
    from_number: str
    to_number: str
    message_type: Optional[str] = None
    body: Optional[str] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    status: Optional[str] = None
    wa_timestamp: Optional[datetime] = None
    contact_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    messages: list[MessageOut]
    total: int


class SendMessageIn(BaseModel):
    to_number: str
    body: str


class SendTemplateIn(BaseModel):
    to_number: str
    template_id: UUID
    variables: Optional[list[str]] = None


class TemplateOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    language: str
    category: Optional[str] = None
    body_text: Optional[str] = None
    components: Optional[Any] = None
    wa_template_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str
    language: str
    category: Optional[str] = None
    body_text: Optional[str] = None
    components: Optional[Any] = None
    wa_template_id: Optional[str] = None


class AutomationRuleCreate(BaseModel):
    name: str
    trigger_event: str
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None
    recipient_type: str
    delay_minutes: int = 0
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_event: Optional[str] = None
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None
    recipient_type: Optional[str] = None
    delay_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class AutomationRuleOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    trigger_event: str
    template_id: Optional[UUID] = None
    message_body: Optional[str] = None
    recipient_type: str
    delay_minutes: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AutomationLogOut(BaseModel):
    id: UUID
    rule_id: UUID
    lead_id: Optional[UUID] = None
    recipient_phone: Optional[str] = None
    rendered_body: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
