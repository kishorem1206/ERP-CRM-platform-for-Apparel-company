"""SQLAlchemy models for the Sales module (customers, quotations, SOs, deliveries, invoices)."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NatureOfBusiness(Base):
    __tablename__ = "nature_of_business"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(300), nullable=False)
    trade_name: Mapped[Optional[str]] = mapped_column(String(300))
    print_name: Mapped[Optional[str]] = mapped_column(String(300))
    internal_id: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    gstin: Mapped[Optional[str]] = mapped_column(String(15))
    pan: Mapped[Optional[str]] = mapped_column(String(10))
    customer_type: Mapped[str] = mapped_column(String(30), default="domestic")
    mobile: Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp_no: Mapped[Optional[str]] = mapped_column(String(20))
    landline_no: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    contact_person_name: Mapped[Optional[str]] = mapped_column(String(200))
    nature_of_business_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("nature_of_business.id"))
    contact_type: Mapped[Optional[str]] = mapped_column(String(50))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    credit_days: Mapped[int] = mapped_column(SmallInteger, default=30)
    payable_opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    receivable_opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    tds_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    enable_tcs: Mapped[bool] = mapped_column(Boolean, default=False)
    due_days: Mapped[int] = mapped_column(SmallInteger, default=0)
    price_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"))
    sales_person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    accounts_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    agent_commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    customer_rating: Mapped[int] = mapped_column(SmallInteger, default=0)
    other_details: Mapped[Optional[str]] = mapped_column(Text)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    customer_portal_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    addresses: Mapped[list["CustomerAddress"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    contacts: Mapped[list["CustomerContact"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    details: Mapped[list["CustomerDetail"]] = relationship(back_populates="customer", cascade="all, delete-orphan", order_by="CustomerDetail.sort_order")
    quotations: Mapped[list["Quotation"]] = relationship(back_populates="customer")
    sales_orders: Mapped[list["SalesOrder"]] = relationship(back_populates="customer")


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    address_type: Mapped[str] = mapped_column(String(20), default="billing")
    line1: Mapped[Optional[str]] = mapped_column(String(300))
    line2: Mapped[Optional[str]] = mapped_column(String(300))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    state_code: Mapped[Optional[int]] = mapped_column(SmallInteger)
    pincode: Mapped[Optional[str]] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(50), default="India")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped["Customer"] = relationship(back_populates="addresses")


class CustomerContact(Base):
    __tablename__ = "customer_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="contacts")


class CustomerDetail(Base):
    __tablename__ = "customer_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="details")


class PriceList(Base):
    __tablename__ = "price_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

    items: Mapped[list["PriceListItem"]] = relationship(back_populates="price_list", cascade="all, delete-orphan")


class PriceListItem(Base):
    __tablename__ = "price_list_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    max_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

    price_list: Mapped["PriceList"] = relationship(back_populates="items")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    price_list_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("price_list_items.id", ondelete="SET NULL"))
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    new_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quotation_number: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_contacts.id"))
    quotation_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    billing_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_addresses.id"))
    price_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("price_lists.id"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    terms: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    converted_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    customer: Mapped["Customer"] = relationship(back_populates="quotations")
    items: Mapped[list["QuotationItem"]] = relationship(back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    hsn_code: Mapped[Optional[str]] = mapped_column(String(8))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    quotation: Mapped["Quotation"] = relationship(back_populates="items")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    quotation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    customer: Mapped["Customer"] = relationship(back_populates="sales_orders")
    items: Mapped[list["SalesOrderItem"]] = relationship(back_populates="sales_order", cascade="all, delete-orphan")
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="sales_order")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="sales_order")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    delivered_qty: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    hsn_code: Mapped[Optional[str]] = mapped_column(String(8))

    sales_order: Mapped["SalesOrder"] = relationship(back_populates="items")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    delivery_number: Mapped[str] = mapped_column(String(50), nullable=False)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    transporter: Mapped[Optional[str]] = mapped_column(String(200))
    lr_number: Mapped[Optional[str]] = mapped_column(String(100))
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(30))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    sales_order: Mapped["SalesOrder"] = relationship(back_populates="deliveries")
    customer: Mapped["Customer"] = relationship()
    items: Mapped[list["DeliveryItem"]] = relationship(back_populates="delivery", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="delivery")


class DeliveryItem(Base):
    __tablename__ = "delivery_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False)
    so_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_order_items.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))

    delivery: Mapped["Delivery"] = relationship(back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"))
    delivery_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cess_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    sales_order: Mapped[Optional["SalesOrder"]] = relationship(back_populates="invoices")
    delivery: Mapped[Optional["Delivery"]] = relationship(back_populates="invoices")
    customer: Mapped["Customer"] = relationship()
