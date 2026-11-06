"""Retail Sales — counter billing kept apart from the B2B sales workflow.

Retail has its own customers (keyed by mobile number), estimates, invoices
(bills) and payments, each with its own numbering. It shares the product
master and the stock ledger with the rest of the ERP: a bill issues stock
out of the retail warehouse, a cancelled bill puts it back.

Prices are GST-inclusive (MRP). A line's net amount is MRP x qty less its
item discount and its share of the bill discount; GST is backed out of that
net amount (taxable = net / (1 + rate/100)).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RetailSettings(Base):
    """One row per company: discount limits and the stock location for bills."""
    __tablename__ = "retail_settings"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True)
    min_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    max_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10"))
    default_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    # Above the maximum only someone with retail.discount_approve may bill;
    # when False the maximum is a hard stop for everyone.
    allow_approved_override: Mapped[bool] = mapped_column(Boolean, default=True)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    credit_days: Mapped[int] = mapped_column(Integer, default=30)
    estimate_validity_days: Mapped[int] = mapped_column(Integer, default=7)
    # Loyalty: 1 point per `amount_per_point` ₹ of eligible paid value; a
    # point is worth `point_value` ₹; points may pay at most `max_redeem_pct`
    # of a bill; points lapse `points_expiry_days` after they're earned (0 = never).
    loyalty_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    amount_per_point: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("100"))
    min_bill_for_points: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    min_redeem_points: Mapped[int] = mapped_column(Integer, default=100)
    point_value: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("1"))
    max_redeem_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20"))
    points_expiry_days: Mapped[int] = mapped_column(Integer, default=365)
    loyalty_excluded_category_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    # Birthday offer: a coupon per customer per birthday, valid in the
    # birthday week (birthday +/- 3 days) or month, made `birthday_lead_days` ahead.
    birthday_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    birthday_discount_type: Mapped[str] = mapped_column(String(10), default="percent")
    birthday_discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10"))
    birthday_min_purchase: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    birthday_max_discount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    birthday_window: Mapped[str] = mapped_column(String(10), default="week")
    birthday_lead_days: Mapped[int] = mapped_column(Integer, default=7)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class RetailSettingsAudit(Base):
    """Every change to the retail settings: who, when, old -> new."""
    __tablename__ = "retail_settings_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(String(200))
    new_value: Mapped[Optional[str]] = mapped_column(String(200))
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetailCustomer(Base):
    __tablename__ = "retail_customers"
    __table_args__ = (UniqueConstraint("company_id", "mobile", name="uq_retail_customers_mobile"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    billing_address: Mapped[Optional[str]] = mapped_column(Text)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    pincode: Mapped[Optional[str]] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")   # active / inactive
    notes: Mapped[Optional[str]] = mapped_column(Text)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)   # balance; the ledger is the record
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # registration date
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class _LineMixin:
    """Columns shared by estimate and invoice lines."""
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(8))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)        # MRP, GST inclusive
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)      # unit_price x qty
    item_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # item + bill share
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)        # incl. GST, after discounts
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class _TotalsMixin:
    bill_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    round_off: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # rounded to the rupee
    discount_approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class RetailEstimate(_TotalsMixin, Base):
    __tablename__ = "retail_estimates"
    __table_args__ = (UniqueConstraint("company_id", "estimate_number", name="uq_retail_estimates_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    estimate_number: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"))
    estimate_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    # draft / sent / accepted / rejected / converted ("expired" is worked out from valid_until)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    converted_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id", use_alter=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Optional["RetailCustomer"]] = relationship()
    items: Mapped[list["RetailEstimateItem"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan", order_by="RetailEstimateItem.sort_order",
    )


class RetailEstimateItem(_LineMixin, Base):
    __tablename__ = "retail_estimate_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_estimates.id", ondelete="CASCADE"), nullable=False)

    estimate: Mapped["RetailEstimate"] = relationship(back_populates="items")


class RetailInvoice(_TotalsMixin, Base):
    __tablename__ = "retail_invoices"
    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_retail_invoices_number"),
        UniqueConstraint("company_id", "client_ref", name="uq_retail_invoices_client_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(30), nullable=False)
    # Set by the billing screen once per bill, so a double-submit can't bill twice.
    client_ref: Mapped[Optional[str]] = mapped_column(String(64))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"))
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(10), nullable=False)          # cash / credit
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False)        # paid / partially_paid / unpaid
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active / cancelled
    estimate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_estimates.id"))
    coupon_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_coupons.id"))
    coupon_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    points_redeemed: Mapped[int] = mapped_column(Integer, default=0)
    points_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    points_awarded: Mapped[bool] = mapped_column(Boolean, default=False)   # credit bills: once fully paid
    # Returns: value handed back, money refunded, points taken back.
    # Outstanding = total - returned - (paid - refunded).
    returned_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    points_returned: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped[Optional["RetailCustomer"]] = relationship()
    items: Mapped[list["RetailInvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="RetailInvoiceItem.sort_order",
    )
    payments: Mapped[list["RetailPayment"]] = relationship(back_populates="invoice", order_by="RetailPayment.created_at")


class RetailInvoiceItem(_LineMixin, Base):
    __tablename__ = "retail_invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id", ondelete="CASCADE"), nullable=False)
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))   # stock cost when billed
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))

    invoice: Mapped["RetailInvoice"] = relationship(back_populates="items")


class RetailPayment(Base):
    """Money received against a retail invoice: the cash at billing, or a
    later collection on a credit bill. Collections are not sales."""
    __tablename__ = "retail_payments"
    __table_args__ = (
        UniqueConstraint("company_id", "client_ref", name="uq_retail_payments_client_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id"), nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(30), nullable=False)
    client_ref: Mapped[Optional[str]] = mapped_column(String(64))
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")   # cash / upi / card / bank
    reference: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active / cancelled
    # Payments made together (one collection across several bills) share a batch and a receipt.
    batch_ref: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    invoice: Mapped["RetailInvoice"] = relationship(back_populates="payments")


class RetailCoupon(Base):
    __tablename__ = "retail_coupons"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_retail_coupons_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")   # manual / promo / birthday
    discount_type: Mapped[str] = mapped_column(String(10), nullable=False)          # percent / fixed
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_purchase: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    max_discount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer)
    per_customer_limit: Mapped[Optional[int]] = mapped_column(Integer)
    product_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    category_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"))
    birthday_year: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Optional["RetailCustomer"]] = relationship()


class RetailCouponRedemption(Base):
    __tablename__ = "retail_coupon_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    coupon_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_coupons.id"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id"), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")   # active / reversed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetailLoyaltyEntry(Base):
    """One line of a customer's points ledger."""
    __tablename__ = "retail_loyalty_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)   # earned / redeemed / expired / adjusted / reversed
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    expires_on: Mapped[Optional[date]] = mapped_column(Date)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetailReturn(Base):
    """Items handed back from a retail bill (a partial return)."""
    __tablename__ = "retail_returns"
    __table_args__ = (
        UniqueConstraint("company_id", "return_number", name="uq_retail_returns_number"),
        UniqueConstraint("company_id", "client_ref", name="uq_retail_returns_client_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    return_number: Mapped[str] = mapped_column(String(30), nullable=False)
    client_ref: Mapped[Optional[str]] = mapped_column(String(64))
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoices.id"), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_customers.id"))
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    return_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)     # incl. GST
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    applied_to_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # reduced what was owed
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))       # paid back
    refund_mode: Mapped[Optional[str]] = mapped_column(String(20))
    points_reversed: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    items: Mapped[list["RetailReturnItem"]] = relationship(back_populates="ret", cascade="all, delete-orphan")
    invoice: Mapped["RetailInvoice"] = relationship()
    customer: Mapped[Optional["RetailCustomer"]] = relationship()


class RetailReturnItem(Base):
    __tablename__ = "retail_return_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_returns.id", ondelete="CASCADE"), nullable=False)
    invoice_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("retail_invoice_items.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))

    ret: Mapped["RetailReturn"] = relationship(back_populates="items")
