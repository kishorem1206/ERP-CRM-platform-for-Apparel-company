import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(50), nullable=False)
    material_type: Mapped[str] = mapped_column(String(20), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    # Textile attributes
    yarn_count: Mapped[Optional[str]] = mapped_column(String(20))
    ply: Mapped[Optional[str]] = mapped_column(String(10))
    mill: Mapped[Optional[str]] = mapped_column(String(200))
    fibre_type: Mapped[Optional[str]] = mapped_column(String(50))
    blend_composition: Mapped[Optional[str]] = mapped_column(Text)   # text summary
    spinning_type: Mapped[Optional[str]] = mapped_column(String(30))
    treatment: Mapped[Optional[str]] = mapped_column(String(50))
    construction: Mapped[Optional[str]] = mapped_column(String(100))
    gsm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    diameter_inches: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    colour: Mapped[Optional[str]] = mapped_column(String(100))
    finish: Mapped[Optional[str]] = mapped_column(String(100))
    # Supplier / invoice
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100))
    invoice_date: Mapped[Optional[date]] = mapped_column(Date)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    # Yarn-specific quantity fields
    bags: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    kg_per_bag: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    # Trim-specific
    trim_type: Mapped[Optional[str]] = mapped_column(String(50))
    trim_unit: Mapped[Optional[str]] = mapped_column(String(30))
    # Split-tracking flags
    split_by_colour: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    split_by_dia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    compositions: Mapped[list["MaterialCompositionItem"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan", lazy="selectin"
    )
    fabric_variants: Mapped[list["FabricVariant"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan", lazy="selectin"
    )
    trim_variants: Mapped[list["TrimVariant"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan", lazy="selectin"
    )


class MaterialCompositionItem(Base):
    __tablename__ = "material_composition_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="CASCADE"), nullable=False
    )
    fibre_name: Mapped[str] = mapped_column(String(100), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lot: Mapped["InventoryLot"] = relationship(back_populates="compositions")


class FabricVariant(Base):
    __tablename__ = "fabric_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="CASCADE"), nullable=False
    )
    colour: Mapped[Optional[str]] = mapped_column(String(100))
    dia_inches: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lot: Mapped["InventoryLot"] = relationship(back_populates="fabric_variants")


class TrimVariant(Base):
    __tablename__ = "trim_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="CASCADE"), nullable=False
    )
    colour: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lot: Mapped["InventoryLot"] = relationship(back_populates="trim_variants")


class FabricRun(Base):
    __tablename__ = "fabric_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    run_number: Mapped[str] = mapped_column(String(50), nullable=False)
    construction: Mapped[Optional[str]] = mapped_column(String(200))
    input_lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    input_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    output_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    wastage_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    wastage_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    output_lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    machine: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    started_at: Mapped[Optional[date]] = mapped_column(Date)
    closed_at: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    material_type: Mapped[str] = mapped_column(String(20), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouse_locations.id"))
    lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    direction: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
