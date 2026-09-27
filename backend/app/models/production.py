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
    """Style Master — the production blueprint for a garment style.

    A LOT is an actual production instance of a Style: it must snapshot the
    Style's configuration (sizes, processes, tolerances, units, rates) at
    creation time. Editing a Style must never retroactively change an
    already-created LOT (see Garments_ERP_Style_Master_Specification.md).
    """
    __tablename__ = "styles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    garment_type: Mapped[Optional[str]] = mapped_column(String(50))
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    season: Mapped[Optional[str]] = mapped_column(String(50))
    final_output_unit: Mapped[Optional[str]] = mapped_column(String(30))   # Pieces / Dozen / Sets / Boxes
    pieces_per_box: Mapped[Optional[int]] = mapped_column(Integer)
    fabric_source: Mapped[str] = mapped_column(String(20), nullable=False, default="yarn")   # yarn / purchased
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    lots: Mapped[list["ProductionLot"]] = relationship(back_populates="style")
    sizes: Mapped[list["StyleSize"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleSize.sort_order")
    colours: Mapped[list["StyleColour"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleColour.sort_order")
    yarns: Mapped[list["StyleYarn"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    fabrics: Mapped[list["StyleFabric"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    processes: Mapped[list["StyleProcess"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleProcess.seq")
    trims: Mapped[list["StyleTrim"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    packing_materials: Mapped[list["StylePackingMaterial"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    additional_costs: Mapped[list["StyleAdditionalCost"]] = relationship(back_populates="style", cascade="all, delete-orphan")


class StyleSize(Base):
    """Applicable size chart for a Style — references the Size Master."""
    __tablename__ = "style_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="sizes")


class StyleColour(Base):
    """Applicable colours for a Style — references the Colour Master."""
    __tablename__ = "style_colours"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    colour_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="colours")


class StyleYarn(Base):
    """Style-specific yarn requirement — references the Yarn Master (inventory_lots)."""
    __tablename__ = "style_yarns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    yarn_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="yarns")


class StyleFabric(Base):
    """Style-specific fabric requirement — references the Fabric Master (inventory_lots)."""
    __tablename__ = "style_fabrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    fabric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    consumption: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    excess_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    gsm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    dyeing_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    printing_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="fabrics")


class StyleProcess(Base):
    """Configurable process in a Style's production workflow.

    Processes are NOT a hard-coded universal sequence: each Style defines its
    own ordered, addable/removable process list with its own tolerance %,
    input/output units, conversion rule, and rate band.
    """
    __tablename__ = "style_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    process_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tolerance_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    input_unit: Mapped[Optional[str]] = mapped_column(String(30))
    output_unit: Mapped[Optional[str]] = mapped_column(String(30))
    conversion_rule: Mapped[Optional[str]] = mapped_column(String(200))
    min_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    max_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    planned_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="processes")
    sub_processes: Mapped[list["StyleSubProcess"]] = relationship(back_populates="process", cascade="all, delete-orphan", order_by="StyleSubProcess.seq")


class StyleSubProcess(Base):
    """Sub-process under a Style process, e.g. Stitching > Power Table / Snitex / Helpers."""
    __tablename__ = "style_sub_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_processes.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    process: Mapped["StyleProcess"] = relationship(back_populates="sub_processes")


class StyleTrim(Base):
    """Style-specific trim requirement — references the Trim Master (inventory_lots)."""
    __tablename__ = "style_trims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    trim_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    category: Mapped[Optional[str]] = mapped_column(String(30))   # Sizable / Non-Sizable
    # seq of the StyleProcess this trim is consumed in (processes are rebuilt on
    # every style update, so the stable seq is stored rather than an FK); NULL = general trim
    process_seq: Mapped[Optional[int]] = mapped_column(SmallInteger)
    excess_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="trims")


class StylePackingMaterial(Base):
    """Style-specific packing material requirement — references the Packing Material Master."""
    __tablename__ = "style_packing_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    excess_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    consumption_stage: Mapped[Optional[str]] = mapped_column(String(50))   # e.g. "During Packing" / "After Ironing"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="packing_materials")


class StyleAdditionalCost(Base):
    """Style-level named cost component outside Fabric/Cutting/Making/Trims.

    Also used to represent Agent Commission (cost_type="agent_commission") rather
    than a separate table, since both are "a named cost line with a planned amount,
    an optional linked party, and an actual value recorded at the LOT" — see
    Garments_ERP_Style_Master_Specification.md §47.14 / §47.28.
    """
    __tablename__ = "style_additional_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    cost_type: Mapped[str] = mapped_column(String(30), nullable=False, default="additional")   # additional / agent_commission
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    basis: Mapped[Optional[str]] = mapped_column(String(30))
    party_vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="additional_costs")


class InternalWorker(Base):
    """Internal worker/operator a production stage can be assigned to, as an
    alternative to an outsourced Vendor — see ProductionStage.assignment_type.
    """
    __tablename__ = "internal_workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role_title: Mapped[Optional[str]] = mapped_column(String(100))
    daily_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class FabricProcessingEntry(Base):
    """Fabric processing (dyeing/printing/other) for a LOT — precedes the
    piece-based garment workflow (§47.3/§47.21) and tracks weight in/out
    separately, since a gain is a valid outcome here (§47.5), not an error the
    way it would be for a garment ProductionStage (see receive_challan()'s
    OUT≤IN guard in services/production.py, which does NOT apply to this model).
    """
    __tablename__ = "fabric_processing_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    process_type: Mapped[str] = mapped_column(String(30), nullable=False)   # dyeing / printing / other
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    in_date: Mapped[date] = mapped_column(Date, nullable=False)
    input_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    out_date: Mapped[Optional[date]] = mapped_column(Date)
    output_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    gain_loss_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    rate_per_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    bill_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_process")   # in_process / completed
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="fabric_processing")


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
    # Weight-based batch fields — additive/parallel to the piece-based fields above
    # so a LOT may be piece-based, weight-based, or both (§47.2).
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id"))
    planned_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    actual_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    season: Mapped[Optional[str]] = mapped_column(String(50))
    target_sp: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    # The actual price this lot's output was/will be sold at — set manually
    # (typically once production data is in, up to and after completion),
    # distinct from target_sp (the pre-production target). Highest-priority
    # source in the actual-selling-price hierarchy (see resolve_selling_prices
    # in services/production.py) and, once set, is pushed onto the produced
    # Product(s)' MRP so Inventory reflects it automatically.
    actual_selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    final_output_unit: Mapped[Optional[str]] = mapped_column(String(30))   # snapshot of Style.final_output_unit
    pieces_per_box: Mapped[Optional[int]] = mapped_column(Integer)         # snapshot of Style.pieces_per_box; editable per lot
    style_version: Mapped[Optional[int]] = mapped_column(Integer)          # snapshot of Style.version at creation
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    style: Mapped[Optional["Style"]] = relationship(back_populates="lots")
    sizes: Mapped[list["ProductionLotSize"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    stages: Mapped[list["ProductionStage"]] = relationship(
        back_populates="production_lot", cascade="all, delete-orphan", order_by="ProductionStage.created_at"
    )
    material_issues: Mapped[list["MaterialIssue"]] = relationship(back_populates="production_lot")
    outputs: Mapped[list["ProductionOutput"]] = relationship(back_populates="production_lot")
    additional_costs: Mapped[list["LotAdditionalCost"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    fabric_processing: Mapped[list["FabricProcessingEntry"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")


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
    style_process_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_processes.id"))
    stage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_qty: Mapped[Optional[int]] = mapped_column(Integer)
    # In-house entry flow ONLY (ProductionStageEntry.pieces_in/pieces_out
    # rollup) — material fed into the stage vs. finished pieces it produced.
    input_qty: Mapped[int] = mapped_column(Integer, default=0)
    output_qty: Mapped[int] = mapped_column(Integer, default=0)
    # Outsourced job-work flow ONLY (ProductionStageChallan rollup) — sent_qty
    # = cumulative OUT to the vendor/worker, received_qty = cumulative IN back.
    # Kept separate from input_qty/output_qty above; previously (incorrectly)
    # reused those columns with an inverted meaning.
    sent_qty: Mapped[int] = mapped_column(Integer, default=0)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)
    rejected_qty: Mapped[int] = mapped_column(Integer, default=0)
    rework_qty: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assignment_type: Mapped[Optional[str]] = mapped_column(String(20))   # "vendor" | "internal_worker" | NULL (in-house)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("internal_workers.id"))
    rate_per_pc: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    bill_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    # Snapshot of the Style process configuration at LOT-creation time — a
    # later edit to the Style Master must not retroactively change this.
    tolerance_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    input_unit: Mapped[Optional[str]] = mapped_column(String(30))
    output_unit: Mapped[Optional[str]] = mapped_column(String(30))
    conversion_rule: Mapped[Optional[str]] = mapped_column(String(200))
    min_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    max_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    planned_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="stages")
    entries: Mapped[list["ProductionStageEntry"]] = relationship(back_populates="stage", cascade="all, delete-orphan")
    challans: Mapped[list["ProductionStageChallan"]] = relationship(back_populates="stage", cascade="all, delete-orphan")


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


class ProductionStageChallan(Base):
    """Job-work challan: material sent OUT from a production stage to an outsourced
    vendor, and received back IN — see Garments_ERP_Style_Master_Specification.md
    §30-36 / §47.7 / §47.8 / §47.11 / §47.12 / §47.26. Distinct from the sales-side
    Delivery model (which is bound to a sales_order/customer, not a production
    stage/vendor).
    """
    __tablename__ = "production_stage_challans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id", ondelete="CASCADE"), nullable=False)
    challan_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("internal_workers.id"))
    out_date: Mapped[date] = mapped_column(Date, nullable=False)
    out_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    in_date: Mapped[Optional[date]] = mapped_column(Date)
    in_qty: Mapped[Optional[int]] = mapped_column(Integer)
    rejected_qty: Mapped[Optional[int]] = mapped_column(Integer)
    expected_return_days: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="out")   # out / partial / received / cancelled
    bill_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    bill_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bill_received_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    stage: Mapped["ProductionStage"] = relationship(back_populates="challans")


class LotAdditionalCost(Base):
    """LOT-level snapshot of a StyleAdditionalCost, with an actual amount recorded
    during execution — mirrors the planned/actual split already used for stages.
    """
    __tablename__ = "lot_additional_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    style_additional_cost_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_additional_costs.id"))
    cost_type: Mapped[str] = mapped_column(String(30), nullable=False, default="additional")
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    planned_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    actual_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    basis: Mapped[Optional[str]] = mapped_column(String(30))
    party_vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="additional_costs")


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
    # First-quality pieces received into sellable FG inventory — unchanged
    # meaning. rejected_qty is recorded alongside for visibility (§47.15) but is
    # NOT passed to InventoryService.receive(); it never enters sellable stock.
    rejected_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="outputs")
