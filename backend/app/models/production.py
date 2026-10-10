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
    # The real sellable Product/SKU master behind this Style (Garments_ERP_Style_Master_Specification.md
    # §4-5). NULL for styles created before this link existed - never retroactively backfilled.
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    product: Mapped[Optional["Product"]] = relationship()
    brand: Mapped[Optional["Brand"]] = relationship()
    lots: Mapped[list["ProductionLot"]] = relationship(back_populates="style")
    sizes: Mapped[list["StyleSize"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleSize.sort_order")
    colours: Mapped[list["StyleColour"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleColour.sort_order")
    part_colours: Mapped[list["StylePartColour"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StylePartColour.sort_order")
    yarns: Mapped[list["StyleYarn"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    fabrics: Mapped[list["StyleFabric"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    processes: Mapped[list["StyleProcess"]] = relationship(back_populates="style", cascade="all, delete-orphan", order_by="StyleProcess.seq")
    trims: Mapped[list["StyleTrim"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    packing_materials: Mapped[list["StylePackingMaterial"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    additional_costs: Mapped[list["StyleAdditionalCost"]] = relationship(back_populates="style", cascade="all, delete-orphan")


class SizeChart(Base):
    """Reusable named size chart (e.g. "T-Shirt Standard") - a group of
    sizes each with its own default quantity, selectable from Style
    Creation instead of re-entering quantities on every Style (spec §1.1).
    """
    __tablename__ = "size_charts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["SizeChartItem"]] = relationship(back_populates="size_chart", cascade="all, delete-orphan", order_by="SizeChartItem.sort_order")


class SizeChartItem(Base):
    __tablename__ = "size_chart_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    size_chart_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("size_charts.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    size_chart: Mapped["SizeChart"] = relationship(back_populates="items")


class StyleSize(Base):
    """Applicable size chart for a Style — references the Size Master.

    quantity/size_chart_id are additive (spec §1.1): quantity may come
    from a linked SizeChartItem's default or be a style-specific override
    (override always wins — see ProductionService._build_style_size).
    """
    __tablename__ = "style_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    size_chart_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("size_charts.id"))
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


class StylePart(Base):
    """Reusable Style Part master (e.g. Front/Back/Collar/Sleeves for a
    shirt, Waistband/Fly for a trouser) — Production Module Reorganisation
    Phase 1. Company-scoped and reusable across styles, exactly like the
    Colour/Brand masters; adding a part to one style never requires a code
    change or affects any other style.
    """
    __tablename__ = "style_parts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StylePartColour(Base):
    """Which colour(s) a given Style's part comes in — mirrors StyleColour
    but scoped per part, since a part may use a different colour than the
    garment's primary colour (e.g. a contrast collar). colour_id is
    nullable: a part can be added before its colour is decided.
    """
    __tablename__ = "style_part_colours"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    style_part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id"), nullable=False)
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="part_colours")
    style_part: Mapped["StylePart"] = relationship()
    sizes: Mapped[list["StylePartSize"]] = relationship(back_populates="style_part_colour", cascade="all, delete-orphan", order_by="StylePartSize.sort_order")


class StylePartSize(Base):
    """Per-size planned quantity for one (style, part, colour) combination —
    mirrors StyleSize, scoped to a StylePartColour row instead of directly
    to the Style, matching the reference ERP's per-part size-wise table
    (spec §5 — operational quantities must never be a single overall figure
    divided equally across sizes).
    """
    __tablename__ = "style_part_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_part_colour_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_part_colours.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    style_part_colour: Mapped["StylePartColour"] = relationship(back_populates="sizes")


class StyleYarn(Base):
    """Style-specific yarn requirement — references the Yarn Master (inventory_lots).

    style_fabric_id/colour_id/counts/consumption_pct were added in
    Production Module Reorganisation Phase 3 (Yarn Planning) so a yarn row
    can represent one component of a specific fabric's blend (e.g. 65%
    Cotton + 35% Polyester composing one "From Yarn" fabric row) — all
    nullable, so existing freestanding yarn rows are unaffected.
    """
    __tablename__ = "style_yarns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    style_fabric_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_fabrics.id", ondelete="CASCADE"))
    yarn_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
    counts: Mapped[Optional[str]] = mapped_column(String(20))   # yarn thickness spec, e.g. "30S"
    consumption_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))   # blend % within the parent fabric
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="yarns")
    style_fabric: Mapped[Optional["StyleFabric"]] = relationship()
    colour: Mapped[Optional["Colour"]] = relationship()


class StyleFabric(Base):
    """Style-specific fabric requirement — references the Fabric Master (inventory_lots).

    style_part_id/colour_id/source_type/knit_dia/finish_dia and the
    size_breakdown relationship were added in Production Module
    Reorganisation Phase 2 (Fabric Requirement/Planning) — all nullable, so
    existing fabric rows from before this phase are unaffected.
    """
    __tablename__ = "style_fabrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    fabric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    style_part_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id", ondelete="SET NULL"))
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
    source_type: Mapped[Optional[str]] = mapped_column(String(20))   # yarn / purchased — NULL inherits Style.fabric_source
    knit_dia: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    finish_dia: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    consumption: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))   # flat fallback when no size_breakdown rows exist
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    excess_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))   # wastage %
    gsm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    dyeing_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    printing_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="fabrics")
    style_part: Mapped[Optional["StylePart"]] = relationship()
    colour: Mapped[Optional["Colour"]] = relationship()
    size_breakdown: Mapped[list["StyleFabricSize"]] = relationship(back_populates="style_fabric", cascade="all, delete-orphan", order_by="StyleFabricSize.sort_order")


class StyleFabricSize(Base):
    """Size-wise fabric consumption — mirrors StyleTrimSize. Absence of rows
    means the parent StyleFabric.consumption figure applies uniformly
    across sizes, matching the Trims size-breakdown convention.
    """
    __tablename__ = "style_fabric_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_fabric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_fabrics.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    style_fabric: Mapped["StyleFabric"] = relationship(back_populates="size_breakdown")


class ProcessMaster(Base):
    """Reusable process definitions (Knitting, Cutting, Making, ...) that a
    Style's process rows can link to for dropdown selection and default
    rate/unit/tolerance values (Garments_ERP spec §1.3/§26 - default vs
    style-specific override; the style-specific value always wins).
    """
    __tablename__ = "process_masters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_unit: Mapped[Optional[str]] = mapped_column(String(30))
    default_tolerance_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    default_min_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    default_max_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    default_planned_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StyleProcess(Base):
    """Configurable process in a Style's production workflow.

    Processes are NOT a hard-coded universal sequence: each Style defines its
    own ordered, addable/removable process list with its own tolerance %,
    input/output units, conversion rule, and rate band.

    style_part_id was added in Production Module Reorganisation Phase 5 —
    a collar may skip a process the front goes through (nullable; NULL
    means the process applies to the whole style, as before this phase).
    """
    __tablename__ = "style_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    style_part_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id", ondelete="SET NULL"))
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    process_name: Mapped[str] = mapped_column(String(100), nullable=False)
    process_master_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("process_masters.id"))
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
    style_part: Mapped[Optional["StylePart"]] = relationship()
    sub_processes: Mapped[list["StyleSubProcess"]] = relationship(back_populates="process", cascade="all, delete-orphan", order_by="StyleSubProcess.seq")


class StyleSubProcess(Base):
    """Sub-process / Operation under a Style process, e.g. Stitching >
    Power Table / Snitex / Helpers. min_rate/max_rate/planned_rate were
    added in Production Module Reorganisation Phase 7 (Wages) — the same
    rate-band fields the parent StyleProcess already has, since an
    operation within a process can be paid a different rate (e.g. an
    Overlock operator vs. a Helper).
    """
    __tablename__ = "style_sub_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_processes.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    max_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    planned_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    process: Mapped["StyleProcess"] = relationship(back_populates="sub_processes")


class StyleTrim(Base):
    """Style-specific trim requirement — references the Trim Master (inventory_lots).

    style_part_id/colour_id were added in Production Module Reorganisation
    Phase 4 (Trims Planning) — a collar may need a different trim than the
    shirt front, and a trim's own colour may differ from its part's colour
    (nullable, so existing trim rows are unaffected).
    """
    __tablename__ = "style_trims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    style_part_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id", ondelete="SET NULL"))
    trim_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"))
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
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
    style_part: Mapped[Optional["StylePart"]] = relationship()
    colour: Mapped[Optional["Colour"]] = relationship()
    size_breakdown: Mapped[list["StyleTrimSize"]] = relationship(back_populates="style_trim", cascade="all, delete-orphan")


class StyleTrimSize(Base):
    """Size-wise trim consumption (spec §21, e.g. S=4 buttons, M=4, L=5,
    XL=5) - only meaningful when the parent StyleTrim.category is
    'Sizable'. Absence of rows here means the trim's flat `quantity`
    applies uniformly regardless of size.
    """
    __tablename__ = "style_trim_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_trim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_trims.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)

    style_trim: Mapped["StyleTrim"] = relationship(back_populates="size_breakdown")


class StylePackingMaterial(Base):
    """Style-specific packing material requirement — references the Packing Material Master."""
    __tablename__ = "style_packing_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))   # per-piece quantity
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    excess_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    consumption_stage: Mapped[Optional[str]] = mapped_column(String(50))   # e.g. "During Packing" / "After Ironing"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style"] = relationship(back_populates="packing_materials")
    product: Mapped[Optional["Product"]] = relationship()


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
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="cutting")   # cutting / checking / packing / completed / cancelled
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
    part_colours: Mapped[list["LotPartColour"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    stages: Mapped[list["ProductionStage"]] = relationship(
        back_populates="production_lot", cascade="all, delete-orphan", order_by="ProductionStage.created_at"
    )
    material_issues: Mapped[list["MaterialIssue"]] = relationship(back_populates="production_lot")
    outputs: Mapped[list["ProductionOutput"]] = relationship(back_populates="production_lot")
    additional_costs: Mapped[list["LotAdditionalCost"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    trims: Mapped[list["LotTrim"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    lot_fabrics: Mapped[list["LotFabric"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    lot_yarns: Mapped[list["LotYarn"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    packing_materials: Mapped[list["LotPackingMaterial"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    fabric_processing: Mapped[list["FabricProcessingEntry"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")
    mistake_logs: Mapped[list["ProductionMistakeLog"]] = relationship(back_populates="production_lot", cascade="all, delete-orphan")


class LotPartColour(Base):
    """LOT-level snapshot of a StylePartColour — Production Module
    Reorganisation Phase 8 (the Order->Style->Part->Colour->Size->Planned
    Quantity hierarchy, at the actual lot/order level rather than the
    style blueprint's template). Pre-filled from the Style's own
    part_colours at lot creation, explicitly overridable per lot — same
    convention as ProductionLotSize mirroring StyleSize.
    """
    __tablename__ = "lot_part_colours"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    style_part_colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_part_colours.id"))
    style_part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id"), nullable=False)
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="part_colours")
    style_part: Mapped["StylePart"] = relationship()
    colour: Mapped[Optional["Colour"]] = relationship()
    sizes: Mapped[list["LotPartSize"]] = relationship(back_populates="lot_part_colour", cascade="all, delete-orphan", order_by="LotPartSize.sort_order")


class LotPartSize(Base):
    """Per-size planned quantity for one LOT (style part, colour)
    combination — mirrors ProductionLotSize, scoped under a LotPartColour
    row instead of directly to the lot.
    """
    __tablename__ = "lot_part_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_part_colour_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lot_part_colours.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    planned_qty: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    lot_part_colour: Mapped["LotPartColour"] = relationship(back_populates="sizes")


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


class ProductionMistakeLog(Base):
    """Per-lot mistake/incident log (16-item request #15): Staff - Process -
    Description - Problem - Action Taken, kept for future reference and
    documentation. staff_id/stage_id link to the existing Worker/Stage
    masters when the person or process is known; the free-text fallbacks
    cover anyone (e.g. a job-work vendor's staff) or anything not already
    tracked as a formal ProductionStage on this lot.
    """
    __tablename__ = "production_mistake_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id", ondelete="SET NULL"))
    process_name: Mapped[Optional[str]] = mapped_column(String(100))
    staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("internal_workers.id", ondelete="SET NULL"))
    staff_name: Mapped[Optional[str]] = mapped_column(String(200))
    mistake_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    problem_type: Mapped[Optional[str]] = mapped_column(String(100))
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="mistake_logs")
    stage: Mapped[Optional["ProductionStage"]] = relationship()
    staff: Mapped[Optional["InternalWorker"]] = relationship()


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
    # Weight-based cutting (spec §9) - rollup totals across this stage's
    # entries, mirroring how input_qty/output_qty already roll up.
    input_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    output_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    wastage_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    recoverable_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
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
    style_process: Mapped[Optional["StyleProcess"]] = relationship()
    sizes: Mapped[list["ProductionStageSize"]] = relationship(back_populates="stage", cascade="all, delete-orphan")


class ProductionAuditLog(Base):
    """Lot status transitions and stage corrections (Phase 11 audit history)."""
    __tablename__ = "production_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(String(50))
    old_value: Mapped[Optional[str]] = mapped_column(String(200))
    new_value: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionStageSize(Base):
    """Size-wise detail for one ProductionStage — Production Module
    Reorganisation Phase 9 (Cutting/Checking/Packing). Mirrors
    ProductionLotSize's shape, scoped per stage instead of per lot.
    Recorded explicitly by floor staff (accepted/rejected/rework per
    size) alongside — not replacing — the stage's own aggregate
    input_qty/output_qty/accepted_qty, which remain the system of
    record for stage-to-stage quantity flow.
    """
    __tablename__ = "production_stage_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id", ondelete="CASCADE"), nullable=False)
    size_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sizes.id"), nullable=False)
    input_qty: Mapped[int] = mapped_column(Integer, default=0)
    accepted_qty: Mapped[int] = mapped_column(Integer, default=0)
    rejected_qty: Mapped[int] = mapped_column(Integer, default=0)
    rework_qty: Mapped[int] = mapped_column(Integer, default=0)
    defect_reason: Mapped[Optional[str]] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    stage: Mapped["ProductionStage"] = relationship(back_populates="sizes")


class ProductionStageEntry(Base):
    __tablename__ = "production_stage_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_stages.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    pieces_in: Mapped[int] = mapped_column(Integer, default=0)
    pieces_out: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    # Weight-based cutting (spec §9) - opt-in per entry; piece-only entries
    # leave these None. wastage_kg/recoverable_kg classify the remainder
    # (input - output) rather than losing track of the balance.
    input_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    output_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    wastage_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    recoverable_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
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


class LotTrim(Base):
    """LOT-level snapshot of a StyleTrim, auto-fetched at LOT creation
    (spec §21: "This should be fetched automatically when the Production
    Lot is created"). planned_qty is computed from the style trim's
    size-wise breakdown (if any) against this LOT's ProductionLotSize
    rows, else the flat quantity x the LOT's total planned_qty.
    """
    __tablename__ = "lot_trims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    style_trim_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_trims.id"))
    trim_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    category: Mapped[Optional[str]] = mapped_column(String(30))
    planned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    actual_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="trims")


class LotFabric(Base):
    """LOT-level snapshot of a StyleFabric — Production Module Reorganisation
    Phase 6 (BOM Consolidation). Mirrors LotTrim: planned_qty is computed
    from the style fabric's size-wise consumption (or flat consumption x
    the LOT's total planned_qty) x excess %.
    """
    __tablename__ = "lot_fabrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    style_fabric_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_fabrics.id"))
    fabric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    style_part_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_parts.id", ondelete="SET NULL"))
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
    source_type: Mapped[Optional[str]] = mapped_column(String(20))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    planned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    actual_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="lot_fabrics")
    style_part: Mapped[Optional["StylePart"]] = relationship()
    colour: Mapped[Optional["Colour"]] = relationship()
    yarns: Mapped[list["LotYarn"]] = relationship(back_populates="lot_fabric", cascade="all, delete-orphan")


class LotYarn(Base):
    """LOT-level snapshot of a StyleYarn — Production Module Reorganisation
    Phase 6. planned_qty is this yarn's consumption_pct share of its
    parent LotFabric's own planned_qty (e.g. a fabric needing 1500kg total,
    blended 65% Cotton / 35% Polyester, needs 975kg Cotton + 525kg
    Polyester). Yarns not assigned to a fabric (pre-Phase-3 freestanding
    rows) get no computed quantity — nothing to scale against.
    """
    __tablename__ = "lot_yarns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    lot_fabric_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("lot_fabrics.id", ondelete="CASCADE"))
    style_yarn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_yarns.id"))
    yarn_name: Mapped[str] = mapped_column(String(200), nullable=False)
    colour_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("colours.id", ondelete="SET NULL"))
    counts: Mapped[Optional[str]] = mapped_column(String(20))
    consumption_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    planned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    actual_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="lot_yarns")
    lot_fabric: Mapped[Optional["LotFabric"]] = relationship(back_populates="yarns")
    colour: Mapped[Optional["Colour"]] = relationship()


class LotPackingMaterial(Base):
    """LOT-level snapshot of a StylePackingMaterial, auto-fetched at LOT
    creation (spec §22/§23). Not size-wise - packing is per total
    finished quantity, unlike trims.
    """
    __tablename__ = "lot_packing_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_lot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_lots.id", ondelete="CASCADE"), nullable=False)
    style_packing_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("style_packing_materials.id"))
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    unit: Mapped[Optional[str]] = mapped_column(String(30))
    consumption_stage: Mapped[Optional[str]] = mapped_column(String(50))
    planned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    actual_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    production_lot: Mapped["ProductionLot"] = relationship(back_populates="packing_materials")
    product: Mapped[Optional["Product"]] = relationship()


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
    # Phase 8 — Lot Creation and Material Issue: a client-generated key, the
    # same one resent if a request is retried, so a duplicate submission
    # returns the original MIS instead of issuing the same stock twice.
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100))
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
    # Return Remainder tracking (spec §18/§19): recorded once the stage's
    # actual consumption is known. used + returned + wastage must never
    # exceed issued_qty (enforced in record_mis_item_return). returned_qty
    # going back to real inventory via InventoryService.receive() IS what
    # makes it "recoverable/resale" - no separate flag needed.
    used_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    returned_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    wastage_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    return_inv_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_transactions.id"))
    return_notes: Mapped[Optional[str]] = mapped_column(Text)

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
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
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
