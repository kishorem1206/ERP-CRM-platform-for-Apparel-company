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
    loyalty_enabled: bool = False
    amount_per_point: Decimal = Decimal("100")
    min_bill_for_points: Decimal = Decimal("0")
    min_redeem_points: int = 100
    point_value: Decimal = Decimal("1")
    max_redeem_pct: Decimal = Decimal("20")
    points_expiry_days: int = 365
    loyalty_excluded_category_ids: list[UUID] = []
    birthday_enabled: bool = False
    birthday_discount_type: str = "percent"
    birthday_discount_value: Decimal = Decimal("10")
    birthday_min_purchase: Decimal = Decimal("0")
    birthday_max_discount: Decimal | None = None
    birthday_window: str = "week"
    birthday_lead_days: int = 7
    updated_at: datetime | None = None


class RetailSettingsUpdate(BaseModel):
    min_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    max_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    default_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    allow_approved_override: bool | None = None
    warehouse_id: UUID | None = None
    credit_days: int | None = Field(default=None, ge=0, le=365)
    estimate_validity_days: int | None = Field(default=None, ge=1, le=365)
    loyalty_enabled: bool | None = None
    amount_per_point: Decimal | None = Field(default=None, gt=0)
    min_bill_for_points: Decimal | None = Field(default=None, ge=0)
    min_redeem_points: int | None = Field(default=None, ge=0)
    point_value: Decimal | None = Field(default=None, gt=0)
    max_redeem_pct: Decimal | None = Field(default=None, ge=0, le=100)
    points_expiry_days: int | None = Field(default=None, ge=0, le=3650)
    loyalty_excluded_category_ids: list[UUID] | None = None
    birthday_enabled: bool | None = None
    birthday_discount_type: Literal["percent", "fixed"] | None = None
    birthday_discount_value: Decimal | None = Field(default=None, gt=0)
    birthday_min_purchase: Decimal | None = Field(default=None, ge=0)
    birthday_max_discount: Decimal | None = Field(default=None, ge=0)
    birthday_window: Literal["week", "month"] | None = None
    birthday_lead_days: int | None = Field(default=None, ge=0, le=60)


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
    loyalty_points: int = 0


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
    coupon_code: str | None = Field(default=None, max_length=30)
    redeem_points: int = Field(default=0, ge=0)


class RetailPaymentOut(BaseModel):
    id: UUID
    receipt_number: str
    payment_date: date
    amount: Decimal
    mode: str
    reference: str | None
    status: str
    batch_ref: UUID | None = None
    cancel_reason: str | None = None
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
    coupon_code: str | None = None
    coupon_discount: Decimal = Decimal("0")
    points_redeemed: int = 0
    points_discount: Decimal = Decimal("0")
    points_earned: int = 0
    points_awarded: bool = False
    returned_amount: Decimal = Decimal("0")
    refunded_amount: Decimal = Decimal("0")
    points_returned: int = 0
    returned_qty: dict[str, Decimal] = {}      # invoice item id -> quantity already returned
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
    coupon_code: str | None = Field(default=None, max_length=30)
    redeem_points: int = Field(default=0, ge=0)
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


# ── Stage 2: coupons, loyalty, birthdays ─────────────────────────────────────

class RetailBillPreview(BaseModel):
    """What a bill comes to, worked out by the server without saving it."""
    gross_amount: Decimal
    discount_amount: Decimal
    coupon_code: str | None
    coupon_discount: Decimal
    points_redeemed: int
    points_discount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    round_off: Decimal
    total_amount: Decimal
    points_earned: int
    points_balance: int | None = None
    max_redeem_points: int | None = None
    lines: list[dict] = []


class RetailCouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    kind: Literal["manual", "promo"] = "manual"
    discount_type: Literal["percent", "fixed"]
    discount_value: Decimal = Field(gt=0)
    min_purchase: Decimal = Field(default=Decimal("0"), ge=0)
    max_discount: Decimal | None = Field(default=None, gt=0)
    start_date: date
    expiry_date: date
    max_uses: int | None = Field(default=None, gt=0)
    per_customer_limit: int | None = Field(default=None, gt=0)
    product_ids: list[UUID] = []
    category_ids: list[UUID] = []
    customer_id: UUID | None = None
    status: Literal["active", "inactive"] = "active"

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        v = v.strip().upper()
        if not all(ch.isalnum() or ch in "-_" for ch in v):
            raise ValueError("Use letters, digits, - or _ in the coupon code")
        return v


class RetailCouponOut(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    kind: str
    discount_type: str
    discount_value: Decimal
    min_purchase: Decimal
    max_discount: Decimal | None
    start_date: date
    expiry_date: date
    max_uses: int | None
    per_customer_limit: int | None
    product_ids: list[UUID]
    category_ids: list[UUID]
    customer_id: UUID | None
    customer_name: str | None = None
    birthday_year: int | None
    status: str
    state: str = "active"          # active / scheduled / expired / used_up / inactive
    times_used: int = 0
    total_discount: Decimal = Decimal("0")
    created_at: datetime


class RetailPointsAdjust(BaseModel):
    points: int
    reason: str = Field(min_length=3)

    @field_validator("points")
    @classmethod
    def _nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Enter the points to add (+) or remove (-)")
        return v


class RetailLoyaltyEntryOut(BaseModel):
    id: UUID
    entry_type: str
    points: int
    balance_after: int
    invoice_id: UUID | None
    invoice_number: str | None = None
    reason: str | None
    expires_on: date | None
    created_at: datetime


# ── Stage 3: credit collections and returns ──────────────────────────────────

class RetailCollectIn(BaseModel):
    """One payment from a customer, settled against their oldest bills first."""
    client_ref: str | None = Field(default=None, max_length=64)
    amount: Decimal = Field(gt=0)
    mode: CollectionMode = "cash"
    payment_date: date | None = None
    reference: str | None = Field(default=None, max_length=100)


class RetailPaymentCancel(BaseModel):
    reason: str = Field(min_length=3)


class RetailReturnLineIn(BaseModel):
    invoice_item_id: UUID
    quantity: Decimal = Field(ge=0)


class RetailReturnCreate(BaseModel):
    client_ref: str | None = Field(default=None, max_length=64)
    items: list[RetailReturnLineIn] = Field(min_length=1)
    reason: str = Field(min_length=3)
    refund_mode: CollectionMode | None = "cash"
    return_date: date | None = None


class RetailReturnItemOut(BaseModel):
    id: UUID
    invoice_item_id: UUID
    description: str
    quantity: Decimal
    amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    model_config = {"from_attributes": True}


class RetailReturnOut(BaseModel):
    id: UUID
    return_number: str
    invoice_id: UUID
    invoice_number: str | None = None
    customer_id: UUID | None
    customer_name: str | None = None
    return_date: date
    reason: str
    return_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    applied_to_balance: Decimal
    refund_amount: Decimal
    refund_mode: str | None
    points_reversed: int
    created_at: datetime
    items: list[RetailReturnItemOut] = []
