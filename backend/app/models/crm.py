import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CrmOrganization(Base):
    __tablename__ = "crm_organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    address: Mapped[Optional[Any]] = mapped_column(JSONB)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    persons: Mapped[list["CrmPerson"]] = relationship(back_populates="organization")
    leads: Mapped[list["CrmLead"]] = relationship(back_populates="organization")


class CrmPerson(Base):
    __tablename__ = "crm_persons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(200))
    emails: Mapped[Any] = mapped_column(JSONB, default=list)
    contact_numbers: Mapped[Any] = mapped_column(JSONB, default=list)
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(50))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_organizations.id", ondelete="SET NULL"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Optional["CrmOrganization"]] = relationship(back_populates="persons")
    leads: Mapped[list["CrmLead"]] = relationship(back_populates="person")
    tags: Mapped[list["CrmTag"]] = relationship(secondary="crm_person_tags", viewonly=True)
    notes: Mapped[list["CrmNote"]] = relationship(back_populates="person", cascade="all, delete-orphan")


class CrmPipeline(Base):
    __tablename__ = "crm_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rotten_days: Mapped[Optional[int]] = mapped_column(Integer, default=30)
    qualified_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    stages: Mapped[list["CrmPipelineStage"]] = relationship(
        back_populates="pipeline",
        order_by="CrmPipelineStage.sort_order",
        cascade="all, delete-orphan",
        foreign_keys="CrmPipelineStage.pipeline_id",
    )


class CrmPipelineStage(Base):
    __tablename__ = "crm_pipeline_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(100))
    color: Mapped[Optional[str]] = mapped_column(String(20), default="#6366f1")
    probability: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    pipeline: Mapped["CrmPipeline"] = relationship(back_populates="stages", foreign_keys=[pipeline_id])
    leads: Mapped[list["CrmLead"]] = relationship(back_populates="stage")


class CrmLeadSource(Base):
    __tablename__ = "crm_lead_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmFollowUpType(Base):
    __tablename__ = "crm_follow_up_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadType(Base):
    __tablename__ = "crm_lead_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLead(Base):
    __tablename__ = "crm_leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    lead_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    temperature: Mapped[str] = mapped_column(String(10), default="cold", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    lost_reason: Mapped[Optional[str]] = mapped_column(Text)
    expected_close_date: Mapped[Optional[date]] = mapped_column(Date)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rotten_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="SET NULL"))
    stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"))
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_lead_sources.id", ondelete="SET NULL"))
    type_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_lead_types.id", ondelete="SET NULL"))
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="SET NULL"))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_organizations.id", ondelete="SET NULL"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    assigned_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    assignment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unassigned")
    next_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    follow_up_type: Mapped[Optional[str]] = mapped_column(String(100))
    follow_up_reason: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_notes: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    contact_outcome: Mapped[Optional[str]] = mapped_column(String(300))
    next_action: Mapped[Optional[str]] = mapped_column(String(300))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)

    # ── Lead Intelligence (normalized intake) ──────────────────────────────
    source_lead_id: Mapped[Optional[str]] = mapped_column(String(200))
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_source_data: Mapped[Optional[Any]] = mapped_column(JSONB)
    normalized_data: Mapped[Optional[Any]] = mapped_column(JSONB)

    # ── Lead Intelligence (scoring) ─────────────────────────────────────────
    score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    priority: Mapped[Optional[str]] = mapped_column(String(10))
    score_version: Mapped[Optional[int]] = mapped_column(SmallInteger)
    score_breakdown: Mapped[Optional[Any]] = mapped_column(JSONB)
    scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ── Lead Intelligence (duplicate / repeat-contact detection) ───────────
    duplicate_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    duplicate_of_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="SET NULL"))
    is_repeat_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Lead Intelligence Phase 2 (response time + escalation) ─────────────
    first_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    response_target_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    escalation_employee_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    escalation_manager_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    pipeline: Mapped[Optional["CrmPipeline"]] = relationship()
    stage: Mapped[Optional["CrmPipelineStage"]] = relationship(back_populates="leads")
    person: Mapped[Optional["CrmPerson"]] = relationship(back_populates="leads")
    organization: Mapped[Optional["CrmOrganization"]] = relationship(back_populates="leads")
    tags: Mapped[list["CrmTag"]] = relationship(secondary="crm_lead_tags", viewonly=True)
    stage_history: Mapped[list["CrmLeadStageHistory"]] = relationship(
        back_populates="lead",
        order_by="CrmLeadStageHistory.changed_at",
        cascade="all, delete-orphan",
    )
    assignment_history: Mapped[list["CrmLeadAssignmentHistory"]] = relationship(
        back_populates="lead",
        order_by="CrmLeadAssignmentHistory.changed_at",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list["CrmNote"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class CrmTag(Base):
    __tablename__ = "crm_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), default="#6366F1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadTag(Base):
    __tablename__ = "crm_lead_tags"

    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_tags.id", ondelete="CASCADE"), primary_key=True)


class CrmPersonTag(Base):
    __tablename__ = "crm_person_tags"

    person_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_tags.id", ondelete="CASCADE"), primary_key=True)


class CrmActivity(Base):
    __tablename__ = "crm_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(300))
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    schedule_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="SET NULL"))
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmProduct(Base):
    __tablename__ = "crm_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sku: Mapped[Optional[str]] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmQuote(Base):
    __tablename__ = "crm_quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quote_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="SET NULL"))
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="SET NULL"))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_organizations.id", ondelete="SET NULL"))
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    terms: Mapped[Optional[str]] = mapped_column(Text)
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lead: Mapped[Optional["CrmLead"]] = relationship()
    person: Mapped[Optional["CrmPerson"]] = relationship()
    organization: Mapped[Optional["CrmOrganization"]] = relationship()
    items: Mapped[list["CrmQuoteItem"]] = relationship(
        back_populates="quote",
        order_by="CrmQuoteItem.sort_order",
        cascade="all, delete-orphan",
    )


class CrmQuoteItem(Base):
    __tablename__ = "crm_quote_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_quotes.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_products.id", ondelete="SET NULL"))
    erp_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    erp_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    quote: Mapped["CrmQuote"] = relationship(back_populates="items")
    product: Mapped[Optional["CrmProduct"]] = relationship()


class CrmEmail(Base):
    __tablename__ = "crm_emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "out" | "in"
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[Optional[str]] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    from_address: Mapped[str] = mapped_column(String(500), nullable=False)
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    bcc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft | sent | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    message_id: Mapped[Optional[str]] = mapped_column(String(500))
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(500))
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="SET NULL"))
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="SET NULL"))
    quote_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_quotes.id", ondelete="SET NULL"))
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    attachments: Mapped[list["CrmEmailAttachment"]] = relationship(back_populates="email", cascade="all, delete-orphan")


class CrmEmailAttachment(Base):
    __tablename__ = "crm_email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_emails.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    email: Mapped["CrmEmail"] = relationship(back_populates="attachments")


class CrmSmtpConfig(Base):
    __tablename__ = "crm_smtp_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(500), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    username: Mapped[str] = mapped_column(String(500), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(300))
    from_email: Mapped[str] = mapped_column(String(500), nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmEmailTemplate(Base):
    __tablename__ = "crm_email_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadImport(Base):
    __tablename__ = "crm_lead_imports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="done")
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="SET NULL"))
    stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class CrmLeadStageHistory(Base):
    __tablename__ = "crm_lead_stage_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False)
    from_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"))
    to_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"))
    from_stage_name: Mapped[Optional[str]] = mapped_column(String(200))
    to_stage_name: Mapped[Optional[str]] = mapped_column(String(200))
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    changed_by_name: Mapped[Optional[str]] = mapped_column(String(300))
    note: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lead: Mapped["CrmLead"] = relationship(back_populates="stage_history")


class CrmLeadAssignmentHistory(Base):
    __tablename__ = "crm_lead_assignment_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False)
    from_assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    to_assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    from_assignee_name: Mapped[Optional[str]] = mapped_column(String(300))
    to_assignee_name: Mapped[Optional[str]] = mapped_column(String(300))
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    changed_by_name: Mapped[Optional[str]] = mapped_column(String(300))
    note: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lead: Mapped["CrmLead"] = relationship(back_populates="assignment_history")


class CrmTask(Base):
    __tablename__ = "crm_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="SET NULL"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadProduct(Base):
    __tablename__ = "crm_lead_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"))
    quantity_interested: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmAdSpend(Base):
    __tablename__ = "crm_ad_spend"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_lead_sources.id", ondelete="SET NULL"))
    campaign: Mapped[Optional[str]] = mapped_column(String(200))
    campaign_id: Mapped[Optional[str]] = mapped_column(String(200))
    ad_set: Mapped[Optional[str]] = mapped_column(String(200))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    impressions: Mapped[Optional[int]] = mapped_column(Integer)
    clicks: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmNote(Base):
    __tablename__ = "crm_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_persons.id", ondelete="CASCADE"))
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_leads.id", ondelete="CASCADE"))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_organizations.id", ondelete="CASCADE"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by_name: Mapped[Optional[str]] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    person: Mapped[Optional["CrmPerson"]] = relationship(back_populates="notes")
    lead: Mapped[Optional["CrmLead"]] = relationship(back_populates="notes")


class CrmLeadScoringRule(Base):
    """One configurable scoring rule (spec Step 22). `code` is the stable
    key the scoring engine references in code; `weight` and `is_active`
    are what an admin edits. Never hardcode weights in the engine - always
    read them from here."""
    __tablename__ = "crm_lead_scoring_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadServiceArea(Base):
    """Configurable preferred/secondary service-area tiers for the location
    scoring signal (spec Step 7). A location with no matching row here is
    treated as untiered ("other"), never penalized."""
    __tablename__ = "crm_lead_service_areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadAssignmentRule(Base):
    """Ordered, company-scoped assignment rule (spec Step 2). The first
    active rule whose conditions all match wins; conditions left null are
    ignored (not required to match)."""
    __tablename__ = "crm_lead_assignment_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_lead_sources.id", ondelete="SET NULL"))
    min_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    location_tier: Mapped[Optional[str]] = mapped_column(String(20))
    assign_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmLeadAssignmentPool(Base):
    """Round-robin candidate list (spec Step 1)."""
    __tablename__ = "crm_lead_assignment_pool"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrmRoundRobinState(Base):
    """Single row per company: who got the last round-robin lead, so the
    next one goes to the next person in the pool's sort_order."""
    __tablename__ = "crm_round_robin_state"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True)
    last_assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
