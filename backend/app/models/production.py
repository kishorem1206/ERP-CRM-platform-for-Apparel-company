"""SQLAlchemy models for the Production module."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Style(Base):
    __tablename__ = "styles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    garment_type: Mapped[Optional[str]] = mapped_column(String(50))
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    season: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lots: Mapped[list["ProductionLot"]] = relationship(back_populates="style")


class ProductionLot(Base):
    __tablename__ = "production_lots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(50), nullable=False)
    style_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"))
    order_ref: Mapped[Optional[str]] = mapped_column(String(100))
    planned_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    season: Mapped[Optional[str]] = mapped_column(String(50))
    target_sp: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    style: Mapped[Optional["Style"]] = relationship(back_populates="lots")
    sizes: Mapped[list["ProductionLotSize"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    stages: Mapped[list["ProductionStage"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    material_issues: Mapped[list["MaterialIssue"]] = relationship(back_populates="production_lot")
    outputs: Mapped[list["ProductionOutput"]] = relationship(back_populates="production_lot")


class ProductionLotSize(Base):
    __tablename__ = "production_lot_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    planned_qty: Mapped[int] = mapped_column(Integer, default=0)
    cut_qty: Mapped[int] = mapped_column(Integer, default=0)
    sewn_qty: Mapped[int] = mapped_column(Integer, default=0)
    finished_qty: Mapped[int] = mapped_column(Integer, default=0)

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="sizes")


class ProductionStage(Base):
    __tablename__ = "production_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id"), nullable=False)
    stage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_qty: Mapped[Optional[int]] = mapped_column(Integer)
    input_qty: Mapped[int] = mapped_column(Integer, default=0)
    output_qty: Mapped[int] = mapped_column(Integer, default=0)
    rejected_qty: Mapped[int] = mapped_column(Integer, default=0)
    rework_qty: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    rate_per_pc: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    bill_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="stages")
    entries: Mapped[list["ProductionStageEntry"]] = relationship(back_populates="stage", cascade="all, delete-orphan")


class ProductionStageEntry(Base):
    __tablename__ = "production_stage_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    pieces_in: Mapped[int] = mapped_column(Integer, default=0)
    pieces_out: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    operator: Mapped[Optional[str]] = mapped_column(String(200))
    machine: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    stage: Mapped["ProductionStage"] = relationship(back_populates="entries")


class MaterialIssue(Base):
    """Material Issue Slip (MIS) — issues raw material from warehouse to production."""
    __tablename__ = "material_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    issue_number: Mapped[str] = mapped_column(String(50), nullable=False)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id"), nullable=False)
    stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="issued")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="material_issues")
    items: Mapped[list["MaterialIssueItem"]] = relationship(back_populates="material_issue", cascade="all, delete-orphan")


class MaterialIssueItem(Base):
    __tablename__ = "material_issue_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("material_issues.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    planned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    issued_qty: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))

    material_issue: Mapped["MaterialIssue"] = relationship(back_populates="items")


class ProductionOutput(Base):
    """Finished-goods output — receives completed garments into FG warehouse."""
    __tablename__ = "production_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    output_number: Mapped[str] = mapped_column(String(50), nullable=False)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    output_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="outputs")
