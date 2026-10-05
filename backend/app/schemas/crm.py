from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ContactValue(BaseModel):
    value: str
    label: str | None = None


# ── Organizations ─────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str
    website: str | None = None
    address: dict[str, Any] | None = None
    assigned_to: UUID | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    address: dict[str, Any] | None = None
    assigned_to: UUID | None = None


class OrganizationOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    website: str | None
    address: dict[str, Any] | None
    assigned_to: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class OrganizationListOut(BaseModel):
    id: UUID
    name: str
    website: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Persons ───────────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    name: str
    job_title: str | None = None
    city: str | None = None
    emails: list[ContactValue] = []
    contact_numbers: list[ContactValue] = []
    whatsapp_number: str | None = None
    organization_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None


class PersonUpdate(BaseModel):
    name: str | None = None
    job_title: str | None = None
    city: str | None = None
    emails: list[ContactValue] | None = None
    contact_numbers: list[ContactValue] | None = None
    whatsapp_number: str | None = None
    organization_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None


class PersonOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    job_title: str | None
    city: str | None
    emails: list[dict]
    contact_numbers: list[dict]
    whatsapp_number: str | None
    organization_id: UUID | None
    customer_id: UUID | None
    assigned_to: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PersonListOut(BaseModel):
    id: UUID
    name: str
    job_title: str | None
    city: str | None
    organization_id: UUID | None
    org_name: str | None = None
    whatsapp_number: str | None
    emails: list[ContactValue] = []
    phone_numbers: list[ContactValue] = []
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Pipelines ─────────────────────────────────────────────────────────────────

class PipelineStageOut(BaseModel):
    id: UUID
    pipeline_id: UUID
    name: str
    code: str | None
    color: str | None
    probability: int | None
    sort_order: int
    is_won: bool
    is_lost: bool
    model_config = {"from_attributes": True}


class PipelineOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    is_default: bool
    rotten_days: int | None
    qualified_stage_id: UUID | None = None
    stages: list[PipelineStageOut] = []
    model_config = {"from_attributes": True}


class QualificationStageUpdate(BaseModel):
    stage_id: UUID | None = None


# ── Lead Source / Type ────────────────────────────────────────────────────────

class LeadSourceOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}


class LeadSourceCreate(BaseModel):
    name: str


class LeadSourceUpdate(BaseModel):
    name: str | None = None


class FollowUpTypeOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}


class LeadTypeOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}


# ── Tags ──────────────────────────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str
    color: str = "#6366F1"


class TagOut(BaseModel):
    id: UUID
    name: str
    color: str | None
    model_config = {"from_attributes": True}


# ── Leads ─────────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    title: str
    description: str | None = None
    lead_value: Decimal = Decimal("0")
    temperature: str = "cold"
    expected_close_date: date | None = None
    pipeline_id: UUID | None = None
    stage_id: UUID | None = None
    source_id: UUID | None = None
    type_id: UUID | None = None
    person_id: UUID | None = None
    organization_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None


class LeadUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    lead_value: Decimal | None = None
    temperature: str | None = None
    expected_close_date: date | None = None
    source_id: UUID | None = None
    type_id: UUID | None = None
    person_id: UUID | None = None
    organization_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None


class LeadStageUpdate(BaseModel):
    stage_id: UUID
    pipeline_id: UUID | None = None


class LeadStatusUpdate(BaseModel):
    status: str
    lost_reason: str | None = None


class LeadAssignIn(BaseModel):
    assigned_to: UUID | None = None
    note: str | None = None


class LeadOut(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    lead_value: Decimal
    temperature: str
    status: str
    lost_reason: str | None
    expected_close_date: date | None
    closed_at: datetime | None
    pipeline_id: UUID | None
    stage_id: UUID | None
    stage_name: str | None = None
    stage_color: str | None = None
    source_id: UUID | None
    type_id: UUID | None
    person_id: UUID | None
    person_name: str | None = None
    person_phone: str | None = None
    person_email: str | None = None
    organization_id: UUID | None
    organization_name: str | None = None
    customer_id: UUID | None
    assigned_to: UUID | None
    assigned_to_name: str | None = None
    assigned_date: datetime | None = None
    assigned_by: UUID | None = None
    assigned_by_name: str | None = None
    assignment_status: str = "unassigned"
    next_follow_up_at: datetime | None = None
    follow_up_type: str | None = None
    follow_up_reason: str | None = None
    follow_up_notes: str | None = None
    follow_up_status: str = "none"
    last_contacted_at: datetime | None = None
    contact_outcome: str | None = None
    next_action: str | None = None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []
    score: int | None = None
    priority: str | None = None
    score_version: int | None = None
    score_breakdown: list[dict] | None = None
    scored_at: datetime | None = None
    duplicate_status: str = "none"
    is_repeat_contact: bool = False
    first_contacted_at: datetime | None = None
    response_target_at: datetime | None = None
    time_to_assignment_minutes: int | None = None
    time_to_first_response_minutes: int | None = None
    sales_order_id: UUID | None = None
    model_config = {"from_attributes": True}


class LeadListOut(BaseModel):
    id: UUID
    title: str
    lead_value: Decimal
    temperature: str
    status: str
    stage_id: UUID | None
    stage_name: str | None = None
    stage_color: str | None = None
    person_id: UUID | None
    person_name: str | None = None
    person_phone: str | None = None
    person_email: str | None = None
    organization_id: UUID | None
    organization_name: str | None = None
    assigned_to: UUID | None
    assigned_to_name: str | None = None
    assignment_status: str = "unassigned"
    next_follow_up_at: datetime | None = None
    follow_up_type: str | None = None
    follow_up_status: str = "none"
    created_at: datetime
    score: int | None = None
    priority: str | None = None
    duplicate_status: str = "none"
    is_repeat_contact: bool = False
    first_contacted_at: datetime | None = None
    response_target_at: datetime | None = None
    sales_order_id: UUID | None = None
    model_config = {"from_attributes": True}


class LeadKanbanStageOut(BaseModel):
    stage_id: UUID
    stage_name: str
    stage_color: str | None
    sort_order: int
    is_won: bool
    is_lost: bool
    column_value: Decimal = Decimal("0")
    leads: list[LeadListOut]


# ── Activities ────────────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    title: str
    type: str
    comment: str | None = None
    location: str | None = None
    schedule_from: datetime | None = None
    schedule_to: datetime | None = None
    lead_id: UUID | None = None
    person_id: UUID | None = None
    assigned_to: UUID | None = None


class ActivityDoneUpdate(BaseModel):
    is_done: bool = True
    outcome: str | None = None
    next_action: str | None = None
    next_follow_up_at: datetime | None = None
    next_follow_up_type: str | None = None
    next_follow_up_reason: str | None = None
    next_follow_up_notes: str | None = None


class ActivityUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    comment: str | None = None
    location: str | None = None
    schedule_from: datetime | None = None
    schedule_to: datetime | None = None
    assigned_to: UUID | None = None


class ActivityOut(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    type: str
    comment: str | None
    location: str | None
    is_done: bool
    schedule_from: datetime | None
    schedule_to: datetime | None
    lead_id: UUID | None
    person_id: UUID | None
    assigned_to: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    lead_title: str | None = None
    person_name: str | None = None
    assigned_to_name: str | None = None
    model_config = {"from_attributes": True}


# ── Tasks (Phase 3) ──────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    notes: str | None = None
    lead_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None
    due_at: datetime | None = None
    priority: str = "medium"
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    lead_id: UUID | None = None
    customer_id: UUID | None = None
    assigned_to: UUID | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None


class TaskCompleteIn(BaseModel):
    notes: str | None = None


class TaskOut(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    notes: str | None
    lead_id: UUID | None
    lead_title: str | None = None
    customer_id: UUID | None
    customer_name: str | None = None
    assigned_to: UUID | None
    assigned_to_name: str | None = None
    due_at: datetime | None
    priority: str
    status: str
    source: str
    created_by: UUID | None
    created_by_name: str | None = None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Ad Spend (Phase 5) ───────────────────────────────────────────────────────

class AdSpendCreate(BaseModel):
    source_id: UUID | None = None
    campaign: str | None = None
    campaign_id: str | None = None
    ad_set: str | None = None
    period_start: date
    period_end: date
    amount: Decimal
    impressions: int | None = None
    clicks: int | None = None
    notes: str | None = None


class AdSpendUpdate(BaseModel):
    source_id: UUID | None = None
    campaign: str | None = None
    campaign_id: str | None = None
    ad_set: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    amount: Decimal | None = None
    impressions: int | None = None
    clicks: int | None = None
    notes: str | None = None


class AdSpendOut(BaseModel):
    id: UUID
    company_id: UUID
    source_id: UUID | None
    source_name: str | None = None
    campaign: str | None
    campaign_id: str | None = None
    ad_set: str | None = None
    period_start: date
    period_end: date
    amount: Decimal
    impressions: int | None = None
    clicks: int | None = None
    source: str = "manual"
    notes: str | None
    created_by: UUID | None
    created_by_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Lead Product Interest (Phase 7) ──────────────────────────────────────────
# References the real ERP product/variant master — not CrmProduct — per the
# Phase 7 instruction to not duplicate product master data.

class LeadProductCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    quantity_interested: Decimal | None = None
    notes: str | None = None


class LeadProductOut(BaseModel):
    id: UUID
    lead_id: UUID
    product_id: UUID | None
    product_name: str | None = None
    variant_id: UUID | None
    variant_sku: str | None = None
    quantity_interested: Decimal | None
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Products ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    sku: str | None = None
    price: Decimal = Decimal("0")
    currency: str = "INR"
    unit: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sku: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    description: str | None
    sku: str | None
    price: Decimal
    currency: str
    unit: str | None
    is_active: bool
    model_config = {"from_attributes": True}


# ── Quotes ────────────────────────────────────────────────────────────────────

class QuoteItemIn(BaseModel):
    product_id: UUID | None = None
    erp_product_id: UUID | None = None
    erp_variant_id: UUID | None = None
    name: str
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal = Decimal("0")


class QuoteItemOut(BaseModel):
    id: UUID
    quote_id: UUID
    product_id: UUID | None
    erp_product_id: UUID | None = None
    erp_variant_id: UUID | None = None
    name: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    total: Decimal
    sort_order: int
    model_config = {"from_attributes": True}


class QuoteCreate(BaseModel):
    title: str
    lead_id: UUID | None = None
    person_id: UUID | None = None
    organization_id: UUID | None = None
    valid_until: date | None = None
    currency: str = "INR"
    discount_percent: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    notes: str | None = None
    terms: str | None = None
    assigned_to: UUID | None = None
    items: list[QuoteItemIn] = []


class QuoteUpdate(BaseModel):
    title: str | None = None
    lead_id: UUID | None = None
    person_id: UUID | None = None
    organization_id: UUID | None = None
    valid_until: date | None = None
    currency: str | None = None
    discount_percent: Decimal | None = None
    tax_amount: Decimal | None = None
    notes: str | None = None
    terms: str | None = None
    assigned_to: UUID | None = None
    items: list[QuoteItemIn] | None = None


class QuoteStatusUpdate(BaseModel):
    status: str


class QuoteOut(BaseModel):
    id: UUID
    company_id: UUID
    quote_number: str
    title: str
    status: str
    lead_id: UUID | None
    lead_title: str | None = None
    person_id: UUID | None
    person_name: str | None = None
    organization_id: UUID | None
    org_name: str | None = None
    valid_until: date | None
    currency: str
    subtotal: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None
    terms: str | None
    sales_order_id: UUID | None
    assigned_to: UUID | None
    created_by: UUID | None
    sent_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemOut] = []
    model_config = {"from_attributes": True}


class QuoteListOut(BaseModel):
    id: UUID
    quote_number: str
    title: str
    status: str
    lead_title: str | None = None
    person_name: str | None = None
    org_name: str | None = None
    total_amount: Decimal
    valid_until: date | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Emails ────────────────────────────────────────────────────────────────────

class EmailCreate(BaseModel):
    subject: str
    body_html: str | None = None
    body_text: str
    to_addresses: list[str]
    cc_addresses: list[str] = []
    bcc_addresses: list[str] = []
    lead_id: UUID | None = None
    person_id: UUID | None = None
    quote_id: UUID | None = None
    in_reply_to: str | None = None

    @field_validator("to_addresses")
    @classmethod
    def validate_to_addresses(cls, v: list[str]) -> list[str]:
        for addr in v:
            if "@" not in addr:
                raise ValueError(f"Invalid email address: {addr}")
        if not v:
            raise ValueError("to_addresses must not be empty")
        return v


class EmailOut(BaseModel):
    id: UUID
    company_id: UUID
    direction: str
    subject: str
    body_text: str
    body_html: str | None
    from_address: str
    to_addresses: list[str]
    cc_addresses: list[str]
    status: str
    lead_id: UUID | None
    person_id: UUID | None
    quote_id: UUID | None
    sent_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class EmailListOut(BaseModel):
    id: UUID
    direction: str
    subject: str
    from_address: str
    to_addresses: list[str]
    status: str
    lead_id: UUID | None
    sent_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── SMTP Config ───────────────────────────────────────────────────────────────

class SmtpConfigCreate(BaseModel):
    host: str
    port: int = 587
    username: str
    password: str
    from_name: str | None = None
    from_email: str
    use_tls: bool = True

    @field_validator("from_email")
    @classmethod
    def validate_from_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid from_email address")
        return v


class SmtpConfigOut(BaseModel):
    id: UUID
    company_id: UUID
    host: str
    port: int
    username: str
    from_name: str | None
    from_email: str
    use_tls: bool
    is_verified: bool
    model_config = {"from_attributes": True}


# ── Lead Conversion ───────────────────────────────────────────────────────────

class LeadConvertIn(BaseModel):
    customer_id: UUID
    order_date: date
    expected_delivery: date | None = None
    notes: str | None = None
    intrastate: bool = True


# ── Email Templates ────────────────────────────────────────────────────────────

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body_text: str
    body_html: str | None = None
    category: str | None = None


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    category: str | None = None
    is_active: bool | None = None


class EmailTemplateOut(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    subject: str
    body_text: str
    body_html: str | None
    category: str | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Lead Import ────────────────────────────────────────────────────────────────

class LeadImportOut(BaseModel):
    id: UUID
    filename: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    status: str
    errors: list
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


# ── Bulk Actions ───────────────────────────────────────────────────────────────

class LeadBulkActionIn(BaseModel):
    lead_ids: list[UUID]
    action: str  # assign / stage / tag / archive
    value: str | None = None


# ── CRM Report Params ─────────────────────────────────────────────────────────

class CrmReportParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    pipeline_id: UUID | None = None


# ── Notes ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    body: str
    person_id: UUID | None = None
    lead_id: UUID | None = None
    organization_id: UUID | None = None


class NoteUpdate(BaseModel):
    body: str


class NoteOut(BaseModel):
    id: UUID
    body: str
    person_id: UUID | None
    lead_id: UUID | None
    organization_id: UUID | None
    created_by: UUID | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Stage History ─────────────────────────────────────────────────────────────

class StageHistoryOut(BaseModel):
    id: UUID
    lead_id: UUID
    from_stage_id: UUID | None
    to_stage_id: UUID | None
    from_stage_name: str | None
    to_stage_name: str | None
    changed_by: UUID | None
    changed_by_name: str | None
    note: str | None
    changed_at: datetime
    model_config = {"from_attributes": True}


class LeadAssignmentHistoryOut(BaseModel):
    id: UUID
    lead_id: UUID
    from_assignee_id: UUID | None
    to_assignee_id: UUID | None
    from_assignee_name: str | None
    to_assignee_name: str | None
    changed_by: UUID | None
    changed_by_name: str | None
    note: str | None
    changed_at: datetime
    model_config = {"from_attributes": True}


class AssignableUserOut(BaseModel):
    id: UUID
    name: str
    email: str


# ── Person 360 (Contact 360 view) ─────────────────────────────────────────────

class LeadForPerson360(BaseModel):
    id: UUID
    title: str
    lead_value: Decimal
    temperature: str
    status: str
    pipeline_id: UUID | None
    pipeline_name: str | None
    stage_id: UUID | None
    stage_name: str | None
    stage_color: str | None
    all_stages: list[dict] = []
    assigned_to: UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class Person360Out(BaseModel):
    id: UUID
    name: str
    job_title: str | None
    city: str | None
    emails: list[dict]
    contact_numbers: list[dict]
    whatsapp_number: str | None
    organization_id: UUID | None
    organization_name: str | None = None
    assigned_to: UUID | None
    created_at: datetime
    leads: list[LeadForPerson360] = []
    activities: list[ActivityOut] = []
    notes: list[NoteOut] = []
    model_config = {"from_attributes": True}


# ── Lead Intelligence ────────────────────────────────────────────────────────

class ScoringRuleOut(BaseModel):
    id: UUID
    category: str
    code: str
    label: str
    weight: int
    is_active: bool
    model_config = {"from_attributes": True}


class ScoringRuleUpdate(BaseModel):
    weight: int | None = None
    is_active: bool | None = None


class ScoringThresholdsOut(BaseModel):
    lead_score_high_threshold: int
    lead_score_medium_threshold: int
    model_config = {"from_attributes": True}


class ScoringThresholdsUpdate(BaseModel):
    lead_score_high_threshold: int | None = Field(default=None, ge=1, le=100)
    lead_score_medium_threshold: int | None = Field(default=None, ge=0, le=99)


class ServiceAreaCreate(BaseModel):
    location_name: str
    tier: str


class ServiceAreaUpdate(BaseModel):
    location_name: str | None = None
    tier: str | None = None


class ServiceAreaOut(BaseModel):
    id: UUID
    location_name: str
    tier: str
    model_config = {"from_attributes": True}


class DuplicateCheckOut(BaseModel):
    status: str
    matched_person_id: UUID | None = None
    matched_organization_id: UUID | None = None
    matched_customer_id: UUID | None = None
    reason: str = ""


class RepeatContactOut(BaseModel):
    previous_lead_id: UUID
    previous_date: datetime
    previous_source: str | None = None
    previous_status: str
    previous_stage_name: str | None = None
    previous_assigned_to_name: str | None = None


# ── Lead Assignment (Phase 2) ────────────────────────────────────────────────

class AssignmentRuleCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True
    source_id: UUID | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    location_tier: str | None = None
    assign_to: UUID


class AssignmentRuleUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    source_id: UUID | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    location_tier: str | None = None
    assign_to: UUID | None = None


class AssignmentRuleOut(BaseModel):
    id: UUID
    name: str
    sort_order: int
    is_active: bool
    source_id: UUID | None
    min_score: int | None
    location_tier: str | None
    assign_to: UUID
    assign_to_name: str | None = None
    model_config = {"from_attributes": True}


class AssignmentPoolMemberIn(BaseModel):
    user_id: UUID
    sort_order: int = 0


class AssignmentPoolMemberOut(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str | None = None
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


class ResponseTargetsOut(BaseModel):
    response_target_high_minutes: int
    response_target_medium_hours: int
    response_target_low_hours: int
    escalation_employee_hours: int
    escalation_manager_hours: int
    model_config = {"from_attributes": True}


class ResponseTargetsUpdate(BaseModel):
    response_target_high_minutes: int | None = Field(default=None, ge=1, le=1440)
    response_target_medium_hours: int | None = Field(default=None, ge=1, le=168)
    response_target_low_hours: int | None = Field(default=None, ge=1, le=336)
    escalation_employee_hours: int | None = Field(default=None, ge=1, le=72)
    escalation_manager_hours: int | None = Field(default=None, ge=1, le=168)


# ── Predictive Scoring (Phase 3) ─────────────────────────────────────────────

class PredictiveScoringReadinessOut(BaseModel):
    ready: bool
    leads_total: int
    leads_total_required: int
    converted: int
    not_converted: int
    outcomes_required_per_class: int
    reason: str
    checked_at: datetime
