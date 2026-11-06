"""Pydantic schemas for the Purchase module."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Vendor ──────────────────────────────────────────────────────────────────

class VendorContactOut(BaseModel):
    id: UUID
    name: str
    phone: str | None
    email: str | None
    designation: str | None = None
    notes: str | None = None
    is_primary: bool

    model_config = {"from_attributes": True}


class VendorBankDetailOut(BaseModel):
    id: UUID
    bank_name: str | None
    account_number: str | None
    ifsc: str | None
    account_name: str | None
    branch: str | None = None
    notes: str | None = None
    is_primary: bool

    model_config = {"from_attributes": True}


class VendorOut(BaseModel):
    id: UUID
    code: str
    name: str
    gstin: str | None
    pan: str | None
    vendor_type: str
    payment_terms: int
    is_active: bool
    supplies_product_types: list[str] | None = None
    contacts: list[VendorContactOut] = []
    bank_details: list[VendorBankDetailOut] = []

    model_config = {"from_attributes": True}


class VendorContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    designation: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_primary: bool = False


class VendorBankDetailCreate(BaseModel):
    bank_name: str | None = Field(default=None, max_length=100)
    account_number: str | None = Field(default=None, max_length=30)
    ifsc: str | None = Field(default=None, max_length=11)
    account_name: str | None = Field(default=None, max_length=100)
    branch: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_primary: bool = False


class VendorTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class VendorCreate(BaseModel):
    code: str
    name: str
    gstin: str | None = None
    pan: str | None = None
    vendor_type: str = "supplier"
    payment_terms: int = 30
    supplies_product_types: list[str] | None = None
    contacts: list[VendorContactCreate] = []
    bank_details: list[VendorBankDetailCreate] = []


class VendorUpdate(BaseModel):
    name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    vendor_type: str | None = None
    payment_terms: int | None = None
    is_active: bool | None = None
    supplies_product_types: list[str] | None = None
    # When given, replace the vendor's contacts / bank accounts with these.
    contacts: list[VendorContactCreate] | None = None
    bank_details: list[VendorBankDetailCreate] | None = None


# ── Purchase Order ───────────────────────────────────────────────────────────

class POItemCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    unit_id: UUID
    ordered_qty: Decimal
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    gst_rate: Decimal = Decimal("0")
    tolerance_pct: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class POItemOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    unit_id: UUID
    product_name: str | None = None
    unit_name: str | None = None
    ordered_qty: Decimal
    received_qty: Decimal
    tolerance_pct: Decimal | None = None
    unit_price: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    gst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    notes: str | None

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    vendor_id: UUID
    warehouse_id: UUID | None = None
    order_date: date
    expected_date: date | None = None
    notes: str | None = None
    terms: str | None = None
    items: list[POItemCreate]
    intrastate: bool = True


class PurchaseOrderUpdate(BaseModel):
    warehouse_id: UUID | None = None
    expected_date: date | None = None
    notes: str | None = None
    terms: str | None = None


class PurchaseOrderOut(BaseModel):
    id: UUID
    po_number: str
    vendor_id: UUID
    vendor_name: str | None = None
    warehouse_id: UUID | None
    order_date: date
    expected_date: date | None
    status: str
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    notes: str | None
    terms: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    close_reason: str | None = None
    close_requested_by_name: str | None = None
    close_requested_at: datetime | None = None
    closed_by_name: str | None = None
    closed_at: datetime | None = None
    items: list[POItemOut] = []

    model_config = {"from_attributes": True}


class POCloseRequest(BaseModel):
    reason: str | None = None


# ── Purchase Entry (GRN) ─────────────────────────────────────────────────────

class GRNItemCreate(BaseModel):
    po_item_id: UUID | None = None
    product_id: UUID
    variant_id: UUID | None = None
    unit_id: UUID
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal = Decimal("0")
    unit_price: Decimal
    quality_status: str = "accepted"
    notes: str | None = None

    @field_validator("quality_status")
    @classmethod
    def validate_quality_status(cls, v: str) -> str:
        allowed = {"pending", "accepted", "rejected", "partial"}
        if v not in allowed:
            raise ValueError(f"quality_status must be one of {allowed}")
        return v


class GRNItemOut(BaseModel):
    id: UUID
    po_item_id: UUID | None
    product_id: UUID
    variant_id: UUID | None
    unit_id: UUID
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    unit_price: Decimal
    total_amount: Decimal
    quality_status: str
    notes: str | None
    inv_transaction_id: UUID | None
    excess_qty: Decimal | None = None

    model_config = {"from_attributes": True}


class PurchaseEntryCreate(BaseModel):
    purchase_order_id: UUID | None = None
    vendor_id: UUID
    warehouse_id: UUID
    entry_date: date
    invoice_number: str | None = None
    invoice_date: date | None = None
    notes: str | None = None
    items: list[GRNItemCreate]


class GRNItemUpdate(BaseModel):
    id: UUID
    received_qty: Decimal
    rejected_qty: Decimal = Decimal("0")
    unit_price: Decimal


class PurchaseEntryUpdate(BaseModel):
    """Admin correction of a saved GRN: header details and, per existing
    line, what arrived, what was rejected and the rate."""
    entry_date: date | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    notes: str | None = None
    items: list[GRNItemUpdate] = []


class PurchaseEntryOut(BaseModel):
    id: UUID
    entry_number: str
    purchase_order_id: UUID | None
    vendor_id: UUID
    vendor_name: str | None = None
    warehouse_id: UUID
    entry_date: date
    invoice_number: str | None
    invoice_date: date | None
    status: str
    taxable_amount: Decimal
    total_amount: Decimal
    notes: str | None
    items: list[GRNItemOut] = []

    model_config = {"from_attributes": True}
