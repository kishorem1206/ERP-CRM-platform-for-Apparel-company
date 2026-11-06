from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PaymentMode = Literal["cash", "credit"]
CollectionMode = Literal["cash", "upi", "card", "bank"]


# ── Settings ──────────────────────────────────────────────────────────────────

class RetailSettingsOut(BaseModel):
    min_discount_pct: Decimal
    max_discount_pct: Decimal
    default_discount_pct: Decimal
    allow_approved_override: bool
    warehouse_id: UUID | None
    warehouse_name: str | None = None
    credit_days: int
    estimate_validity_days: int
    updated_at: datetime | None = None


class RetailSettingsUpdate(BaseModel):
    min_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    max_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    default_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    allow_approved_override: bool | None = None
    warehouse_id: UUID | None = None
    credit_days: int | None = Field(default=None, ge=0, le=365)
    estimate_validity_days: int | None = Field(default=None, ge=1, le=365)


class RetailSettingsAuditOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_by_name: str | None = None
    changed_at: datetime


# ── Customers ─────────────────────────────────────────────────────────────────

def _mobile(v: str) -> str:
    digits = "".join(ch for ch in v if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10:
        raise ValueError("Mobile number should have 10 digits")
    return digits


class RetailCustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mobile: str
    email: str | None = Field(default=None, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    billing_address: str | None = None
    shipping_address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)
    notes: str | None = None

    @field_validator("mobile")
    @classmethod
    def _check_mobile(cls, v: str) -> str:
        return _mobile(v)


class RetailCustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    mobile: str | None = None
    email: str | None = Field(default=None, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    billing_address: str | None = None
    shipping_address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)
    status: Literal["active", "inactive"] | None = None
    notes: str | None = None

    @field_validator("mobile")
    @classmethod
    def _check_mobile(cls, v: str | None) -> str | None:
        return _mobile(v) if v else v


class RetailCustomerOut(BaseModel):
    id: UUID
    name: str
    mobile: str
    email: str | None
    date_of_birth: date | None
    gender: str | None
    billing_address: str | None
    shipping_address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    status: str
    notes: str | None
    created_at: datetime
    # Worked out from the customer's bills (cancelled bills don't count).
    purchase_count: int = 0
    total_spent: Decimal = Decimal("0")
    products_purchased: Decimal = Decimal("0")
    last_purchase_date: date | None = None
    outstanding: Decimal = Decimal("0")


# ── Bills and estimates ───────────────────────────────────────────────────────

class RetailLineIn(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    quantity: Decimal = Field(gt=0)
    item_discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    # Only used when the product has no MRP set; otherwise the MRP is the price.
    unit_price: Decimal | None = Field(default=None, ge=0)


class RetailLineOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    description: str
    hsn_code: str | None
    quantity: Decimal
    unit_price: Decimal
    gross_amount: Decimal
    item_discount_pct: Decimal
    discount_amount: Decimal
    gst_rate: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    net_amount: Decimal
    model_config = {"from_attributes": True}


class _TotalsOut(BaseModel):
    bill_discount_pct: Decimal
    gross_amount: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    round_off: Decimal
    total_amount: Decimal
    notes: str | None


class RetailInvoiceCreate(BaseModel):
    client_ref: str | None = Field(default=None, max_length=64)
    customer_id: UUID | None = None
    invoice_date: date | None = None
    payment_mode: PaymentMode = "cash"
    # Cash bills are paid in full; a credit bill may take part payment now.
    amount_paid_now: Decimal | None = Field(default=None, ge=0)
    collection_mode: CollectionMode = "cash"
    bill_discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    items: list[RetailLineIn] = Field(min_length=1)
    notes: str | None = None
    estimate_id: UUID | None = None


class RetailPaymentOut(BaseModel):
    id: UUID
    receipt_number: str
    payment_date: date
    amount: Decimal
    mode: str
    reference: str | None
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class RetailInvoiceOut(_TotalsOut):
    id: UUID
    invoice_number: str
    customer_id: UUID | None
    customer_name: str | None = None
    customer_mobile: str | None = None
    invoice_date: date
    warehouse_id: UUID
    payment_mode: str
    payment_status: str
    amount_paid: Decimal
    outstanding: Decimal
    due_date: date | None
    status: str
    estimate_id: UUID | None
    cancel_reason: str | None
    created_at: datetime
    discount_approved: bool = False
    items: list[RetailLineOut] = []
    payments: list[RetailPaymentOut] = []


class RetailInvoiceListOut(BaseModel):
    id: UUID
    invoice_number: str
    customer_name: str | None
    customer_mobile: str | None
    invoice_date: date
    payment_mode: str
    payment_status: str
    total_amount: Decimal
    amount_paid: Decimal
    outstanding: Decimal
    status: str


class RetailInvoiceCancel(BaseModel):
    reason: str = Field(min_length=1)


class RetailPaymentCreate(BaseModel):
    client_ref: str | None = Field(default=None, max_length=64)
    amount: Decimal = Field(gt=0)
    payment_date: date | None = None
    mode: CollectionMode = "cash"
    reference: str | None = Field(default=None, max_length=100)


class RetailEstimateCreate(BaseModel):
    customer_id: UUID | None = None
    estimate_date: date | None = None
    valid_until: date | None = None
    bill_discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    items: list[RetailLineIn] = Field(min_length=1)
    notes: str | None = None


class RetailEstimateStatus(BaseModel):
    status: Literal["draft", "sent", "accepted", "rejected"]


class RetailEstimateConvert(BaseModel):
    client_ref: str | None = Field(default=None, max_length=64)
    payment_mode: PaymentMode = "cash"
    amount_paid_now: Decimal | None = Field(default=None, ge=0)
    collection_mode: CollectionMode = "cash"


class RetailEstimateOut(_TotalsOut):
    id: UUID
    estimate_number: str
    customer_id: UUID | None
    customer_name: str | None = None
    customer_mobile: str | None = None
    estimate_date: date
    valid_until: date | None
    status: str          # includes "expired", worked out from valid_until
    converted_invoice_id: UUID | None
    converted_invoice_number: str | None = None
    created_at: datetime
    items: list[RetailLineOut] = []


class RetailProductOut(BaseModel):
    """One sellable row for the billing search: a variant, or a product without variants."""
    product_id: UUID
    variant_id: UUID | None
    name: str
    sku: str | None
    barcode: str | None
    size: str | None
    colour: str | None
    mrp: Decimal | None
    gst_rate: Decimal
    hsn_code: str | None
    in_stock: Decimal
