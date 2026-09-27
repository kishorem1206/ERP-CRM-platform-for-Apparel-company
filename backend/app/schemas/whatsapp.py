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
