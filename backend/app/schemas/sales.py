"""Pydantic schemas for the Sales module."""
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


# ── Nature of Business ────────────────────────────────────────────────────────

class NatureOfBusinessOut(BaseModel):
    id: UUID
    name: str
    is_active: bool
    sort_order: int
    model_config = {"from_attributes": True}


# ── Customer ─────────────────────────────────────────────────────────────────

class CustomerAddressOut(BaseModel):
    id: UUID
    address_type: str
    line1: str | None
    line2: str | None
    city: str | None
    state: str | None
    state_code: int | None
    pincode: str | None
    country: str
    is_default: bool
    model_config = {"from_attributes": True}


class CustomerContactOut(BaseModel):
    id: UUID
    name: str
    designation: str | None
    phone: str | None
    email: str | None
    is_primary: bool
    model_config = {"from_attributes": True}


class CustomerDetailOut(BaseModel):
    id: UUID
    label: str | None
    value: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class CustomerOut(BaseModel):
    id: UUID
    code: str
    legal_name: str
    trade_name: str | None
    print_name: str | None
    internal_id: str | None
    location: str | None
    gstin: str | None
    pan: str | None
    customer_type: str
    mobile: str | None
    whatsapp_no: str | None
    landline_no: str | None
    email: str | None
    contact_person_name: str | None
    nature_of_business_id: UUID | None
    contact_type: str | None
    credit_limit: Decimal
    credit_days: int
    payable_opening_balance: Decimal
    receivable_opening_balance: Decimal
    discount_percent: Decimal
    tds_percent: Decimal
    enable_tcs: bool
    due_days: int
    accounts_manager_id: UUID | None
    agent_id: UUID | None
    agent_commission_percent: Decimal
    customer_rating: int
    other_details: str | None
    remarks: str | None
    customer_portal_enabled: bool
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    addresses: list[CustomerAddressOut] = []
    contacts: list[CustomerContactOut] = []
    details: list[CustomerDetailOut] = []
    model_config = {"from_attributes": True}


class CustomerListOut(BaseModel):
    id: UUID
    code: str
    legal_name: str
    trade_name: str | None
    mobile: str | None
    email: str | None
    gstin: str | None
    customer_type: str
    is_active: bool
    model_config = {"from_attributes": True}


class CustomerAddressCreate(BaseModel):
    address_type: str = "billing"
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    state_code: int | None = None
    pincode: str | None = None
    country: str = "India"
    is_default: bool = False


class CustomerContactCreate(BaseModel):
    name: str
    designation: str | None = None
    phone: str | None = None
    email: str | None = None
    is_primary: bool = False


class CustomerDetailCreate(BaseModel):
    label: str | None = None
    value: str | None = None
    sort_order: int = 0


_GSTIN_RE = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)

def _validate_gstin(v: str | None) -> str | None:
    if v and not _GSTIN_RE.match(v.upper()):
        raise ValueError("Invalid GSTIN format")
    return v.upper() if v else v


class CustomerCreate(BaseModel):
    code: str
    legal_name: str
    trade_name: str | None = None
    print_name: str | None = None
    internal_id: str | None = None
    location: str | None = None
    gstin: str | None = None
    pan: str | None = None
    customer_type: str = "domestic"
    mobile: str | None = None
    whatsapp_no: str | None = None
    landline_no: str | None = None
    email: str | None = None
    contact_person_name: str | None = None
    nature_of_business_id: UUID | None = None
    contact_type: str | None = None
    credit_limit: Decimal = Decimal("0")
    credit_days: int = 30
    payable_opening_balance: Decimal = Decimal("0")
    receivable_opening_balance: Decimal = Decimal("0")
    discount_percent: Decimal = Decimal("0")
    tds_percent: Decimal = Decimal("0")
    enable_tcs: bool = False
    due_days: int = 0
    price_list_id: UUID | None = None
    sales_person_id: UUID | None = None
    accounts_manager_id: UUID | None = None
    agent_id: UUID | None = None
    agent_commission_percent: Decimal = Decimal("0")
    customer_rating: int = 0
    other_details: str | None = None
    remarks: str | None = None
    customer_portal_enabled: bool = False
    addresses: list[CustomerAddressCreate] = []
    contacts: list[CustomerContactCreate] = []
    details: list[CustomerDetailCreate] = []

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: str) -> str:
        if v not in {"domestic", "export", "sez"}:
            raise ValueError("customer_type must be domestic, export, or sez")
        return v

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        return _validate_gstin(v)


class CustomerUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    print_name: str | None = None
    internal_id: str | None = None
    location: str | None = None
    gstin: str | None = None
    pan: str | None = None
    customer_type: str | None = None
    mobile: str | None = None
    whatsapp_no: str | None = None
    landline_no: str | None = None
    email: str | None = None
    contact_person_name: str | None = None
    nature_of_business_id: UUID | None = None
    contact_type: str | None = None
    credit_limit: Decimal | None = None
    credit_days: int | None = None
    payable_opening_balance: Decimal | None = None
    receivable_opening_balance: Decimal | None = None
    discount_percent: Decimal | None = None
    tds_percent: Decimal | None = None
    enable_tcs: bool | None = None
    due_days: int | None = None
    price_list_id: UUID | None = None
    sales_person_id: UUID | None = None
    accounts_manager_id: UUID | None = None
    agent_id: UUID | None = None
    agent_commission_percent: Decimal | None = None
    customer_rating: int | None = None
    other_details: str | None = None
    remarks: str | None = None
    customer_portal_enabled: bool | None = None
    is_active: bool | None = None
    addresses: list[CustomerAddressCreate] | None = None
    contacts: list[CustomerContactCreate] | None = None
    details: list[CustomerDetailCreate] | None = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        return _validate_gstin(v)


# ── Quotation ─────────────────────────────────────────────────────────────────

class QuotationItemCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    description: str | None = None
    quantity: Decimal
    unit_id: UUID
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    gst_rate: Decimal = Decimal("0")
    hsn_code: str | None = None
    sort_order: int = 0


class QuotationItemOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    description: str | None
    quantity: Decimal
    unit_id: UUID
    unit_price: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    gst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    hsn_code: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class QuotationCreate(BaseModel):
    customer_id: UUID
    quotation_date: date
    valid_until: date | None = None
    notes: str | None = None
    terms: str | None = None
    intrastate: bool = True
    items: list[QuotationItemCreate]


class QuotationUpdate(BaseModel):
    valid_until: date | None = None
    notes: str | None = None
    terms: str | None = None


class QuotationOut(BaseModel):
    id: UUID
    quotation_number: str
    customer_id: UUID
    customer_name: str | None = None
    quotation_date: date
    valid_until: date | None
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    notes: str | None
    terms: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    converted_order_id: UUID | None
    items: list[QuotationItemOut] = []
    model_config = {"from_attributes": True}


# ── Sales Order ───────────────────────────────────────────────────────────────

class SOItemCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    quantity: Decimal
    unit_id: UUID
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    gst_rate: Decimal = Decimal("0")
    hsn_code: str | None = None


class SOItemOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    quantity: Decimal
    delivered_qty: Decimal
    unit_id: UUID
    unit_price: Decimal
    discount_pct: Decimal
    taxable_amount: Decimal
    gst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    hsn_code: str | None
    model_config = {"from_attributes": True}


class SalesOrderCreate(BaseModel):
    customer_id: UUID
    quotation_id: UUID | None = None
    order_date: date
    expected_delivery: date | None = None
    notes: str | None = None
    intrastate: bool = True
    items: list[SOItemCreate]


class SalesOrderUpdate(BaseModel):
    expected_delivery: date | None = None
    notes: str | None = None


class SalesOrderOut(BaseModel):
    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str | None = None
    quotation_id: UUID | None
    order_date: date
    expected_delivery: date | None
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    notes: str | None
    items: list[SOItemOut] = []
    model_config = {"from_attributes": True}


# ── Delivery ──────────────────────────────────────────────────────────────────

class DeliveryItemCreate(BaseModel):
    so_item_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    quantity: Decimal
    unit_id: UUID
    unit_price: Decimal


class DeliveryItemOut(BaseModel):
    id: UUID
    so_item_id: UUID
    product_id: UUID
    variant_id: UUID | None
    quantity: Decimal
    unit_id: UUID
    unit_price: Decimal
    total_amount: Decimal
    inv_transaction_id: UUID | None
    model_config = {"from_attributes": True}


class DeliveryCreate(BaseModel):
    sales_order_id: UUID
    warehouse_id: UUID
    delivery_date: date
    transporter: str | None = None
    lr_number: str | None = None
    vehicle_number: str | None = None
    notes: str | None = None
    items: list[DeliveryItemCreate]


class DeliveryOut(BaseModel):
    id: UUID
    delivery_number: str
    sales_order_id: UUID
    customer_id: UUID
    customer_name: str | None = None
    warehouse_id: UUID
    delivery_date: date
    status: str
    transporter: str | None
    lr_number: str | None
    vehicle_number: str | None
    notes: str | None
    dispatched_at: datetime | None
    items: list[DeliveryItemOut] = []
    model_config = {"from_attributes": True}


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    sales_order_id: UUID | None = None
    delivery_id: UUID | None = None
    customer_id: UUID
    invoice_date: date
    due_date: date | None = None
    notes: str | None = None


class InvoiceOut(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: UUID
    customer_name: str | None = None
    sales_order_id: UUID | None
    delivery_id: UUID | None
    invoice_date: date
    due_date: date | None
    status: str
    subtotal: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    notes: str | None
    model_config = {"from_attributes": True}


# ── Price Lists (Phase 7) ────────────────────────────────────────────────────

class PriceListCreate(BaseModel):
    name: str
    is_default: bool = False
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListOut(BaseModel):
    id: UUID
    name: str
    is_default: bool
    valid_from: date | None
    valid_to: date | None
    item_count: int = 0
    model_config = {"from_attributes": True}


class PriceListItemCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    customer_id: UUID | None = None
    min_quantity: Decimal = Decimal("0")
    max_quantity: Decimal | None = None
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListItemUpdate(BaseModel):
    product_id: UUID | None = None
    variant_id: UUID | None = None
    customer_id: UUID | None = None
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None
    unit_price: Decimal | None = None
    discount_pct: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListItemOut(BaseModel):
    id: UUID
    price_list_id: UUID
    product_id: UUID
    product_name: str | None = None
    variant_id: UUID | None
    variant_sku: str | None = None
    customer_id: UUID | None
    customer_name: str | None = None
    min_quantity: Decimal
    max_quantity: Decimal | None
    unit_price: Decimal
    discount_pct: Decimal
    valid_from: date | None
    valid_to: date | None
    model_config = {"from_attributes": True}


class PriceResolveOut(BaseModel):
    unit_price: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    source: str


class PriceHistoryOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    old_price: Decimal | None
    new_price: Decimal
    changed_by_name: str | None = None
    changed_at: datetime
    model_config = {"from_attributes": True}
