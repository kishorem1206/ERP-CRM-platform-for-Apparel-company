"""Pydantic schemas for the Production module."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


# ── Style Master ──────────────────────────────────────────────────────────────
# The Style Master is the production blueprint for a garment style — see
# Garments_ERP_Style_Master_Specification.md. It is deliberately comprehensive:
# variants, materials (referencing masters), a configurable process workflow
# with per-process tolerance/units/rates, trim planning, and packing-material
# planning. None of these sections should be removed to "simplify" the form.

class StyleSizeIn(BaseModel):
    size_id: UUID
    sort_order: int = 0
    quantity: Decimal | None = None
    size_chart_id: UUID | None = None


class StyleSizeOut(BaseModel):
    id: UUID
    size_id: UUID
    sort_order: int
    quantity: Decimal | None = None
    size_chart_id: UUID | None = None
    model_config = {"from_attributes": True}


# ── Size Chart Master ───────────────────────────────────────────────────────

class SizeChartItemIn(BaseModel):
    size_id: UUID
    quantity: Decimal | None = None
    sort_order: int = 0


class SizeChartItemOut(BaseModel):
    id: UUID
    size_id: UUID
    quantity: Decimal | None
    sort_order: int
    model_config = {"from_attributes": True}


class SizeChartCreate(BaseModel):
    name: str
    items: list[SizeChartItemIn] = []


class SizeChartOut(BaseModel):
    id: UUID
    name: str
    items: list[SizeChartItemOut] = []
    model_config = {"from_attributes": True}


class StyleColourIn(BaseModel):
    colour_id: UUID
    sort_order: int = 0


class StyleColourOut(BaseModel):
    id: UUID
    colour_id: UUID
    sort_order: int
    model_config = {"from_attributes": True}


class StylePartOut(BaseModel):
    id: UUID
    name: str
    is_active: bool
    model_config = {"from_attributes": True}


class StylePartCreate(BaseModel):
    name: str


class StylePartSizeIn(BaseModel):
    size_id: UUID
    quantity: Decimal | None = None
    sort_order: int = 0


class StylePartSizeOut(BaseModel):
    id: UUID
    size_id: UUID
    quantity: Decimal | None
    sort_order: int
    model_config = {"from_attributes": True}


class StylePartColourIn(BaseModel):
    style_part_id: UUID
    colour_id: UUID | None = None
    sort_order: int = 0
    sizes: list[StylePartSizeIn] = []


class StylePartColourOut(BaseModel):
    id: UUID
    style_part_id: UUID
    style_part_name: str | None = None
    colour_id: UUID | None
    sort_order: int
    sizes: list[StylePartSizeOut] = []
    model_config = {"from_attributes": True}


class StyleYarnIn(BaseModel):
    yarn_name: str
    lot_id: UUID | None = None
    fabric_index: int | None = None   # index into this request's `fabrics` list — which fabric this yarn composes
    colour_id: UUID | None = None
    counts: str | None = None
    consumption_pct: Decimal | None = None   # blend % within the parent fabric
    quantity: Decimal | None = None
    unit: str | None = None
    notes: str | None = None


class StyleYarnOut(BaseModel):
    id: UUID
    yarn_name: str
    lot_id: UUID | None
    style_fabric_id: UUID | None = None
    fabric_name: str | None = None
    colour_id: UUID | None = None
    colour_name: str | None = None
    counts: str | None = None
    consumption_pct: Decimal | None = None
    quantity: Decimal | None
    unit: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleFabricSizeIn(BaseModel):
    size_id: UUID
    quantity: Decimal


class StyleFabricSizeOut(BaseModel):
    size_id: UUID
    quantity: Decimal
    model_config = {"from_attributes": True}


class StyleFabricIn(BaseModel):
    fabric_name: str
    lot_id: UUID | None = None
    style_part_id: UUID | None = None
    colour_id: UUID | None = None
    source_type: str | None = None   # yarn / purchased — omit to inherit the Style's own fabric_source
    knit_dia: Decimal | None = None
    finish_dia: Decimal | None = None
    consumption: Decimal | None = None
    unit: str | None = None
    excess_pct: Decimal | None = None
    gsm: Decimal | None = None
    dyeing_rate: Decimal | None = None
    printing_rate: Decimal | None = None
    notes: str | None = None
    size_breakdown: list[StyleFabricSizeIn] = []

    @field_validator("source_type")
    @classmethod
    def _validate_source_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("yarn", "purchased"):
            raise ValueError("source_type must be 'yarn' or 'purchased'")
        return v


class StyleFabricOut(BaseModel):
    id: UUID
    fabric_name: str
    lot_id: UUID | None
    style_part_id: UUID | None = None
    style_part_name: str | None = None
    colour_id: UUID | None = None
    source_type: str | None = None
    knit_dia: Decimal | None = None
    finish_dia: Decimal | None = None
    consumption: Decimal | None
    unit: str | None
    excess_pct: Decimal | None
    gsm: Decimal | None
    dyeing_rate: Decimal | None
    printing_rate: Decimal | None
    notes: str | None
    size_breakdown: list[StyleFabricSizeOut] = []
    stock_available: Decimal | None = None
    model_config = {"from_attributes": True}


class StyleSubProcessIn(BaseModel):
    seq: int = 0
    name: str
    min_rate: Decimal | None = None
    max_rate: Decimal | None = None
    planned_rate: Decimal | None = None
    notes: str | None = None


class StyleSubProcessOut(BaseModel):
    id: UUID
    seq: int
    name: str
    min_rate: Decimal | None = None
    max_rate: Decimal | None = None
    planned_rate: Decimal | None = None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleProcessIn(BaseModel):
    seq: int = 0
    process_name: str
    process_master_id: UUID | None = None
    style_part_id: UUID | None = None
    is_enabled: bool = True
    tolerance_pct: Decimal | None = None
    input_unit: str | None = None
    output_unit: str | None = None
    conversion_rule: str | None = None
    min_rate: Decimal | None = None
    max_rate: Decimal | None = None
    planned_rate: Decimal | None = None
    notes: str | None = None
    sub_processes: list[StyleSubProcessIn] = []


class StyleProcessOut(BaseModel):
    id: UUID
    seq: int
    process_name: str
    process_master_id: UUID | None = None
    style_part_id: UUID | None = None
    style_part_name: str | None = None
    is_enabled: bool
    tolerance_pct: Decimal | None
    input_unit: str | None
    output_unit: str | None
    conversion_rule: str | None
    min_rate: Decimal | None
    max_rate: Decimal | None
    planned_rate: Decimal | None
    notes: str | None
    sub_processes: list[StyleSubProcessOut] = []
    model_config = {"from_attributes": True}


class StyleAdditionalCostIn(BaseModel):
    cost_type: str = "additional"   # additional / agent_commission
    description: str
    amount: Decimal | None = None
    basis: str | None = None
    party_vendor_id: UUID | None = None
    notes: str | None = None

    @field_validator("cost_type")
    @classmethod
    def _validate_cost_type(cls, v: str) -> str:
        allowed = {"additional", "agent_commission"}
        if v not in allowed:
            raise ValueError(f"cost_type must be one of {allowed}")
        return v


class StyleAdditionalCostOut(BaseModel):
    id: UUID
    cost_type: str
    description: str
    amount: Decimal | None
    basis: str | None
    party_vendor_id: UUID | None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleTrimSizeIn(BaseModel):
    size_id: UUID
    quantity: Decimal


class StyleTrimSizeOut(BaseModel):
    size_id: UUID
    quantity: Decimal
    model_config = {"from_attributes": True}


class StyleTrimIn(BaseModel):
    trim_name: str
    lot_id: UUID | None = None
    style_part_id: UUID | None = None
    colour_id: UUID | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    category: str | None = None   # Sizable / Non-Sizable
    process_seq: int | None = None
    excess_pct: Decimal | None = None
    notes: str | None = None
    size_breakdown: list[StyleTrimSizeIn] = []   # §21 — only meaningful when category == "Sizable"

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Sizable", "Non-Sizable"):
            raise ValueError("category must be 'Sizable' or 'Non-Sizable'")
        return v


class StyleTrimOut(BaseModel):
    id: UUID
    trim_name: str
    lot_id: UUID | None
    style_part_id: UUID | None = None
    style_part_name: str | None = None
    colour_id: UUID | None = None
    colour_name: str | None = None
    quantity: Decimal | None
    unit: str | None
    category: str | None
    process_seq: int | None = None
    excess_pct: Decimal | None
    notes: str | None
    size_breakdown: list[StyleTrimSizeOut] = []
    model_config = {"from_attributes": True}


class StylePackingMaterialIn(BaseModel):
    material_name: str
    product_id: UUID | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    excess_pct: Decimal | None = None
    consumption_stage: str | None = None
    notes: str | None = None


class StylePackingMaterialOut(BaseModel):
    id: UUID
    material_name: str
    product_id: UUID | None = None
    quantity: Decimal | None
    unit: str | None
    excess_pct: Decimal | None
    consumption_stage: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleCreate(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    garment_type: str | None = None
    gender: str | None = None
    season: str | None = None
    final_output_unit: str | None = None   # Pieces / Dozen / Sets / Boxes
    pieces_per_box: int | None = None
    fabric_source: str = "yarn"            # yarn / purchased
    target_price: Decimal | None = None
    product_id: UUID | None = None   # link an existing Product; omit to auto-create one
    brand_id: UUID | None = None
    sizes: list[StyleSizeIn] = []
    colours: list[StyleColourIn] = []
    part_colours: list[StylePartColourIn] = []
    yarns: list[StyleYarnIn] = []
    fabrics: list[StyleFabricIn] = []
    processes: list[StyleProcessIn] = []
    trims: list[StyleTrimIn] = []
    packing_materials: list[StylePackingMaterialIn] = []
    additional_costs: list[StyleAdditionalCostIn] = []

    @model_validator(mode="after")
    def _validate_yarn_blend(self) -> "StyleCreate":
        """Spec §Phase 3: 'For blended yarn, validate the composition
        percentages' — every fabric's assigned yarns must sum to ~100% once
        any of them specifies a consumption_pct, so a blend can't silently
        under- or over-account for what composes the fabric.
        """
        by_fabric: dict[int, list[Decimal]] = {}
        for y in self.yarns:
            if y.fabric_index is None or y.consumption_pct is None:
                continue
            if y.fabric_index < 0 or y.fabric_index >= len(self.fabrics):
                raise ValueError(f"Yarn '{y.yarn_name}' references fabric_index {y.fabric_index}, which doesn't exist")
            by_fabric.setdefault(y.fabric_index, []).append(y.consumption_pct)
        for idx, pcts in by_fabric.items():
            total = sum(pcts)
            if not (Decimal("99") <= total <= Decimal("101")):
                fabric_name = self.fabrics[idx].fabric_name
                raise ValueError(f"Yarn composition for fabric '{fabric_name}' totals {total}%, must total 100%")
        return self


class TargetPriceSuggestion(BaseModel):
    process_name: str
    current_rate: Decimal
    suggested_rate: Decimal
    delta: Decimal


class TargetPriceCheckOut(BaseModel):
    planned_process_cost: Decimal
    target_price: Decimal
    gap: Decimal   # >0 = over budget, <=0 = cushion (magnitude = headroom)
    message: str
    suggestions: list[TargetPriceSuggestion] = []


class StyleOut(BaseModel):
    id: UUID
    name: str
    code: str | None
    garment_type: str | None
    gender: str | None
    season: str | None
    final_output_unit: str | None
    pieces_per_box: int | None = None
    fabric_source: str = "yarn"
    target_price: Decimal | None = None
    version: int
    is_active: bool
    product_id: UUID | None = None
    brand_id: UUID | None = None
    brand_name: str | None = None
    model_config = {"from_attributes": True}


class StyleDetailOut(BaseModel):
    id: UUID
    name: str
    code: str | None
    description: str | None
    garment_type: str | None
    gender: str | None
    season: str | None
    final_output_unit: str | None
    pieces_per_box: int | None = None
    fabric_source: str = "yarn"
    target_price: Decimal | None = None
    version: int
    is_active: bool
    product_id: UUID | None = None
    product_code: str | None = None
    brand_id: UUID | None = None
    brand_name: str | None = None
    hsn_id: UUID | None = None
    gst_rate: Decimal | None = None
    sizes: list[StyleSizeOut] = []
    colours: list[StyleColourOut] = []
    part_colours: list[StylePartColourOut] = []
    yarns: list[StyleYarnOut] = []
    fabrics: list[StyleFabricOut] = []
    processes: list[StyleProcessOut] = []
    trims: list[StyleTrimOut] = []
    packing_materials: list[StylePackingMaterialOut] = []
    additional_costs: list[StyleAdditionalCostOut] = []
    target_price_check: TargetPriceCheckOut | None = None
    total_tolerance_pct: Decimal | None = None
    model_config = {"from_attributes": True}


# ── Production Lot ────────────────────────────────────────────────────────────

class LotSizeCreate(BaseModel):
    size_id: UUID
    planned_qty: int


class LotSizeOut(BaseModel):
    id: UUID
    size_id: UUID
    planned_qty: int
    cut_qty: int
    sewn_qty: int
    finished_qty: int
    model_config = {"from_attributes": True}


class LotPartSizeCreate(BaseModel):
    size_id: UUID
    planned_qty: int = 0


class LotPartSizeOut(BaseModel):
    size_id: UUID
    planned_qty: int
    model_config = {"from_attributes": True}


class LotPartColourCreate(BaseModel):
    style_part_id: UUID
    colour_id: UUID | None = None
    sort_order: int = 0
    sizes: list[LotPartSizeCreate] = []


class LotPartColourOut(BaseModel):
    id: UUID
    style_part_id: UUID
    style_part_name: str | None = None
    colour_id: UUID | None
    colour_name: str | None = None
    sort_order: int
    sizes: list[LotPartSizeOut] = []
    model_config = {"from_attributes": True}


class LotAdditionalCostCreate(BaseModel):
    cost_type: str = "additional"   # additional / agent_commission
    description: str
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    basis: str | None = None
    party_vendor_id: UUID | None = None
    notes: str | None = None

    @field_validator("cost_type")
    @classmethod
    def _validate_cost_type(cls, v: str) -> str:
        if v not in ("additional", "agent_commission"):
            raise ValueError("cost_type must be 'additional' or 'agent_commission'")
        return v


class ProductionLotCreate(BaseModel):
    lot_number: str | None = None
    style_id: UUID | None = None
    customer_id: UUID | None = None
    sales_order_id: UUID | None = None
    order_ref: str | None = None
    planned_qty: int
    colour_id: UUID
    planned_weight_kg: Decimal | None = None
    delivery_date: date | None = None
    season: str | None = None
    target_sp: Decimal | None = None
    pieces_per_box: int | None = None   # defaults to the Style's
    notes: str | None = None
    sizes: list[LotSizeCreate] = []
    part_colours: list[LotPartColourCreate] = []
    additional_costs: list[LotAdditionalCostCreate] = []   # optional, per lot


class ProductionLotUpdate(BaseModel):
    pieces_per_box: int | None = None
    delivery_date: date | None = None
    season: str | None = None
    target_sp: Decimal | None = None
    actual_selling_price: Decimal | None = None
    notes: str | None = None


# ── Internal Worker ───────────────────────────────────────────────────────────

class InternalWorkerCreate(BaseModel):
    name: str
    phone: str | None = None
    role_title: str | None = None
    daily_rate: Decimal | None = None


class InternalWorkerOut(BaseModel):
    id: UUID
    name: str
    phone: str | None
    role_title: str | None
    daily_rate: Decimal | None
    is_active: bool
    model_config = {"from_attributes": True}


# ── Production Stage ──────────────────────────────────────────────────────────

class StageCreate(BaseModel):
    stage_type: str
    stage_name: str
    planned_qty: int | None = None
    assignment_type: str | None = None   # "vendor" | "internal_worker" | None
    vendor_id: UUID | None = None
    worker_id: UUID | None = None
    rate_per_pc: Decimal | None = None
    notes: str | None = None

    @field_validator("stage_type")
    @classmethod
    def validate_stage_type(cls, v: str) -> str:
        allowed = {"cutting", "making", "finishing", "qc", "packing", "dispatch"}
        if v not in allowed:
            raise ValueError(f"stage_type must be one of {allowed}")
        return v

    @field_validator("assignment_type")
    @classmethod
    def validate_assignment_type(cls, v: str | None) -> str | None:
        if v is not None and v not in {"vendor", "internal_worker"}:
            raise ValueError("assignment_type must be 'vendor' or 'internal_worker'")
        return v


class StageUpdate(BaseModel):
    stage_name: str | None = None
    planned_qty: int | None = None
    assignment_type: str | None = None
    vendor_id: UUID | None = None
    worker_id: UUID | None = None
    rate_per_pc: Decimal | None = None
    # Corrections to recorded quantities (§7 — editing a stage). Validated in
    # ProductionService.update_stage(): received_qty + rejected_qty <= sent_qty.
    sent_qty: int | None = None
    received_qty: int | None = None
    rejected_qty: int | None = None
    # Phase 11 — before this field existed, nothing could ever set a stage to
    # "completed", so advance_lot_status's gate (every stage of the current
    # bucket must be "completed") could never actually be cleared. The floor
    # supervisor marks a stage done explicitly; no quantity threshold is
    # enforced here because "done" is a judgment call the system shouldn't
    # second-guess once input/output have been recorded.
    status: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("pending", "in_progress", "completed"):
            raise ValueError("status must be one of: pending, in_progress, completed")
        return v


# ── Stage Entry ───────────────────────────────────────────────────────────────

class StageEntryCreate(BaseModel):
    entry_date: date
    pieces_in: int = 0
    pieces_out: int = 0
    rejected: int = 0
    input_weight_kg: Decimal | None = None
    output_weight_kg: Decimal | None = None
    wastage_kg: Decimal | None = None
    recoverable_kg: Decimal | None = None
    operator: str | None = None
    machine: str | None = None
    notes: str | None = None


class StageEntryOut(BaseModel):
    id: UUID
    entry_date: date
    pieces_in: int
    pieces_out: int
    rejected: int
    input_weight_kg: Decimal | None = None
    output_weight_kg: Decimal | None = None
    wastage_kg: Decimal | None = None
    recoverable_kg: Decimal | None = None
    operator: str | None
    machine: str | None
    notes: str | None
    model_config = {"from_attributes": True}


# ── Stage Challan (Job Work OUT/IN) ──────────────────────────────────────────

class StageChallanCreate(BaseModel):
    vendor_id: UUID | None = None
    worker_id: UUID | None = None
    out_date: date
    out_qty: int
    expected_return_days: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_one_assignee(self) -> "StageChallanCreate":
        # A plain @field_validator on worker_id would miss the case where
        # BOTH fields are left at their None default (pydantic v2 skips
        # field_validator for unprovided fields unless validate_default=
        # True) - confirmed live: a challan with neither field was wrongly
        # accepted. model_validator always runs regardless.
        if bool(self.vendor_id) == bool(self.worker_id):
            raise ValueError("Exactly one of vendor_id or worker_id is required")
        return self


class StageChallanReceive(BaseModel):
    in_date: date
    in_qty: int
    rejected_qty: int | None = None   # defaults to out_qty - in_qty when omitted
    bill_amount: Decimal | None = None
    notes: str | None = None


class StageChallanBillUpdate(BaseModel):
    bill_received: bool
    bill_received_date: date | None = None
    notes: str | None = None


class StageChallanOut(BaseModel):
    id: UUID
    challan_number: str
    vendor_id: UUID | None
    worker_id: UUID | None
    out_date: date
    out_qty: int
    in_date: date | None
    in_qty: int | None
    rejected_qty: int | None
    pending_qty: int = 0   # computed: out_qty - (in_qty or 0) - (rejected_qty or 0)
    expected_return_days: int | None
    status: str
    bill_amount: Decimal | None
    bill_received: bool
    bill_received_date: date | None
    notes: str | None
    model_config = {"from_attributes": True}


class StageSizeUpdate(BaseModel):
    accepted_qty: int | None = None
    rejected_qty: int | None = None
    rework_qty: int | None = None
    defect_reason: str | None = None


class StageSizeOut(BaseModel):
    id: UUID
    size_id: UUID
    input_qty: int
    accepted_qty: int
    rejected_qty: int
    rework_qty: int
    pending_qty: int = 0   # computed: input - accepted - rejected - rework, floored at 0
    defect_reason: str | None
    model_config = {"from_attributes": True}


class StageOut(BaseModel):
    id: UUID
    stage_type: str
    stage_name: str
    planned_qty: int | None
    input_qty: int
    output_qty: int
    sent_qty: int
    received_qty: int
    accepted_qty: int = 0   # computed: received_qty if assigned else output_qty — flows to next stage's planned_qty
    rejected_qty: int
    rework_qty: int
    status: str
    assignment_type: str | None
    vendor_id: UUID | None
    worker_id: UUID | None
    rate_per_pc: Decimal | None
    bill_amount: Decimal | None
    notes: str | None
    tolerance_pct: Decimal | None = None
    input_unit: str | None = None
    output_unit: str | None = None
    conversion_rule: str | None = None
    min_rate: Decimal | None = None
    max_rate: Decimal | None = None
    planned_rate: Decimal | None = None
    input_weight_kg: Decimal | None = None
    output_weight_kg: Decimal | None = None
    wastage_kg: Decimal | None = None
    recoverable_kg: Decimal | None = None
    variance_kg: Decimal | None = None
    permitted_tolerance_kg: Decimal | None = None
    within_tolerance: bool | None = None
    weight_per_piece: Decimal | None = None
    effective_rate_per_kg: Decimal | None = None
    operations: list["StageOperationOut"] = []
    sizes: list[StageSizeOut] = []
    # What still looks unrecorded on this stage — shown as a warning (not a
    # block) when the user marks it complete.
    completion_warnings: list[str] = []
    entries: list[StageEntryOut] = []
    challans: list[StageChallanOut] = []
    model_config = {"from_attributes": True}


class StageOperationOut(BaseModel):
    """Read-only attribution of this stage's own actual cost (bill_amount, or
    rate_per_pc x accepted_qty) across its configured Operations (Phase 7 —
    Wages), by each operation's relative planned_rate weight. Purely a
    computed view of the stage's existing single total — never a separate
    stored amount — so it can never double-count against it."""
    name: str
    planned_rate: Decimal | None = None
    estimated_cost_share: Decimal | None = None


# ── LOT Additional Cost / Agent Commission ───────────────────────────────────

class LotAdditionalCostOut(BaseModel):
    id: UUID
    cost_type: str
    description: str
    planned_amount: Decimal | None
    actual_amount: Decimal | None
    basis: str | None
    party_vendor_id: UUID | None
    notes: str | None
    model_config = {"from_attributes": True}


class LotAdditionalCostUpdate(BaseModel):
    actual_amount: Decimal | None = None
    notes: str | None = None


class MistakeLogCreate(BaseModel):
    stage_id: UUID | None = None
    process_name: str | None = None
    staff_id: UUID | None = None
    staff_name: str | None = None
    mistake_date: date
    description: str
    problem_type: str | None = None
    action_taken: str | None = None


class MistakeLogOut(BaseModel):
    id: UUID
    production_lot_id: UUID
    stage_id: UUID | None
    stage_name: str | None = None
    process_name: str | None
    staff_id: UUID | None
    staff_name: str | None
    resolved_staff_name: str | None = None
    mistake_date: date
    description: str
    problem_type: str | None
    action_taken: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class LotTrimOut(BaseModel):
    id: UUID
    style_trim_id: UUID | None
    trim_name: str
    unit: str | None
    category: str | None
    planned_qty: Decimal | None
    actual_qty: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


class LotTrimActualUpdate(BaseModel):
    actual_qty: Decimal | None = None
    notes: str | None = None


class LotFabricOut(BaseModel):
    id: UUID
    style_fabric_id: UUID | None
    fabric_name: str
    unit: str | None
    planned_qty: Decimal | None
    actual_qty: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


class LotFabricActualUpdate(BaseModel):
    actual_qty: Decimal | None = None
    notes: str | None = None


class LotYarnOut(BaseModel):
    id: UUID
    style_yarn_id: UUID | None
    yarn_name: str
    unit: str | None
    planned_qty: Decimal | None
    actual_qty: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


class LotYarnActualUpdate(BaseModel):
    actual_qty: Decimal | None = None
    notes: str | None = None


class LotPackingMaterialOut(BaseModel):
    id: UUID
    style_packing_material_id: UUID | None
    material_name: str
    product_id: UUID | None = None
    product_name: str | None = None
    unit: str | None
    consumption_stage: str | None
    planned_qty: Decimal | None
    actual_qty: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


class LotPackingActualUpdate(BaseModel):
    actual_qty: Decimal | None = None
    notes: str | None = None


# ── Fabric Processing (dyeing/printing) ──────────────────────────────────────

class FabricProcessingCreate(BaseModel):
    process_type: str
    vendor_id: UUID | None = None
    in_date: date
    input_kg: Decimal
    rate_per_kg: Decimal | None = None
    notes: str | None = None

    @field_validator("process_type")
    @classmethod
    def _validate_process_type(cls, v: str) -> str:
        allowed = {"dyeing", "printing", "other"}
        if v not in allowed:
            raise ValueError(f"process_type must be one of {allowed}")
        return v


class FabricProcessingComplete(BaseModel):
    out_date: date
    output_kg: Decimal
    bill_amount: Decimal | None = None
    notes: str | None = None


class FabricProcessingUpdate(BaseModel):
    """Correct any field after the fact — before or after completion (e.g. fix
    a typo'd input_kg, reassign the vendor, or amend the bill once it arrives).
    """
    vendor_id: UUID | None = None
    in_date: date | None = None
    input_kg: Decimal | None = None
    out_date: date | None = None
    output_kg: Decimal | None = None
    rate_per_kg: Decimal | None = None
    bill_amount: Decimal | None = None
    notes: str | None = None


class FabricProcessingOut(BaseModel):
    id: UUID
    process_type: str
    vendor_id: UUID | None
    in_date: date
    input_kg: Decimal
    out_date: date | None
    output_kg: Decimal | None
    gain_loss_kg: Decimal | None
    rate_per_kg: Decimal | None
    bill_amount: Decimal | None
    status: str
    notes: str | None
    model_config = {"from_attributes": True}


# ── LOT Cost Summary ──────────────────────────────────────────────────────────

class LotCostComponentOut(BaseModel):
    name: str
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    variance_amount: Decimal | None = None
    variance_pct: Decimal | None = None
    note: str | None = None


class BomLineOut(BaseModel):
    id: UUID
    category: str   # yarn / fabric / trim / packing
    name: str
    style_part_name: str | None = None
    colour_name: str | None = None
    unit: str | None = None
    required_qty: Decimal | None = None
    available_qty: Decimal | None = None   # None = no specific batch linked, not computable
    shortage_qty: Decimal | None = None
    is_informational: bool = False   # e.g. fabric produced from yarn — not separately procured
    notes: str | None = None


class StageSummaryBucket(BaseModel):
    stage_type: str
    label: str
    input_qty: int = 0
    accepted_qty: int = 0
    rejected_qty: int = 0
    rework_qty: int = 0
    pending_qty: int = 0


class LotProductionSummaryOut(BaseModel):
    """The "Completed (Consolidated)" view (Phase 9) — every figure here is
    derived from stage transactions (ProductionStageSize rollups), never a
    separately-maintained total, per the spec's own rule."""
    production_lot_id: UUID
    lot_number: str
    planned_qty: int
    cut_qty: int = 0
    checked_qty: int = 0
    accepted_qty: int = 0
    packed_qty: int = 0
    rejected_qty: int = 0
    rework_qty: int = 0
    remaining_qty: int = 0
    buckets: list[StageSummaryBucket] = []


class LotBomOut(BaseModel):
    production_lot_id: UUID
    lot_number: str
    yarn: list[BomLineOut] = []
    fabric: list[BomLineOut] = []
    trims: list[BomLineOut] = []
    packing_materials: list[BomLineOut] = []
    total_lines: int
    shortage_lines: int


class LotCostSummaryOut(BaseModel):
    components: list[LotCostComponentOut] = []
    total_planned: Decimal | None = None
    total_actual: Decimal
    first_quality_qty: Decimal
    rejected_qty: Decimal
    total_output_qty: Decimal
    yield_pct: Decimal | None = None
    cost_per_first_quality_piece: Decimal | None = None
    target_price: Decimal | None = None
    target_revenue: Decimal | None = None
    expected_margin_pct: Decimal | None = None
    actual_selling_price_per_piece: Decimal | None = None
    selling_price_source: str | None = None
    actual_revenue: Decimal | None = None
    profit_per_piece: Decimal | None = None
    actual_profit: Decimal | None = None
    gross_margin_pct: Decimal | None = None
    is_final: bool = False
    missing_rate_warnings: list[str] = []


class ProductionLotOut(BaseModel):
    id: UUID
    lot_number: str
    style_id: UUID | None
    style_name: str | None = None
    customer_id: UUID | None
    sales_order_id: UUID | None
    order_ref: str | None
    planned_qty: int
    actual_qty: int
    colour_id: UUID | None = None
    planned_weight_kg: Decimal | None = None
    actual_weight_kg: Decimal | None = None
    delivery_date: date | None
    season: str | None
    target_sp: Decimal | None
    actual_selling_price: Decimal | None = None
    status: str
    notes: str | None
    final_output_unit: str | None = None
    pieces_per_box: int | None = None
    style_version: int | None = None
    closed_at: datetime | None
    sizes: list[LotSizeOut] = []
    part_colours: list[LotPartColourOut] = []
    stages: list[StageOut] = []
    additional_costs: list[LotAdditionalCostOut] = []
    trims: list[LotTrimOut] = []
    packing_materials: list[LotPackingMaterialOut] = []
    boxes_required: int | None = None
    fabric_blockers: list[str] = []   # §33 fabric-first: why garment work can't start yet
    fabric_processing: list[FabricProcessingOut] = []
    cost_summary: LotCostSummaryOut
    model_config = {"from_attributes": True}


# ── Material Issue (MIS) ──────────────────────────────────────────────────────

class MISItemCreate(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    planned_qty: Decimal | None = None
    issued_qty: Decimal
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")


class MISItemOut(BaseModel):
    id: UUID
    product_id: UUID
    variant_id: UUID | None
    product_name: str | None = None
    unit_abbreviation: str | None = None
    planned_qty: Decimal | None
    issued_qty: Decimal
    unit_id: UUID
    unit_cost: Decimal
    total_cost: Decimal
    material_lot_id: UUID | None = None
    material_lot_number: str | None = None
    inv_transaction_id: UUID | None
    excess_qty: Decimal | None = None   # computed: max(issued_qty - planned_qty, 0) — §47.4
    used_qty: Decimal | None = None
    returned_qty: Decimal | None = None
    wastage_qty: Decimal | None = None
    return_inv_transaction_id: UUID | None = None
    return_notes: str | None = None
    model_config = {"from_attributes": True}


class MISItemReturnUpdate(BaseModel):
    used_qty: Decimal | None = None
    returned_qty: Decimal | None = None
    wastage_qty: Decimal | None = None
    notes: str | None = None


class MaterialIssueCreate(BaseModel):
    production_lot_id: UUID
    stage_id: UUID | None = None
    warehouse_id: UUID
    issue_date: date
    notes: str | None = None
    items: list[MISItemCreate]
    idempotency_key: str | None = None


class MaterialIssueOut(BaseModel):
    id: UUID
    issue_number: str
    production_lot_id: UUID
    lot_number: str | None = None
    stage_id: UUID | None
    stage_name: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    issue_date: date
    status: str
    notes: str | None
    items: list[MISItemOut] = []
    model_config = {"from_attributes": True}


# ── Production Output ─────────────────────────────────────────────────────────

class ProductionOutputCreate(BaseModel):
    production_lot_id: UUID
    warehouse_id: UUID
    output_date: date
    product_id: UUID
    variant_id: UUID | None = None
    quantity: Decimal
    rejected_qty: Decimal | None = None
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")


class ProductionOutputOut(BaseModel):
    id: UUID
    output_number: str
    production_lot_id: UUID
    lot_number: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    output_date: date
    product_id: UUID
    product_name: str | None = None
    variant_id: UUID | None = None
    quantity: Decimal
    rejected_qty: Decimal | None
    unit_id: UUID
    unit_abbreviation: str | None = None
    unit_cost: Decimal
    total_cost: Decimal
    inv_transaction_id: UUID | None
    model_config = {"from_attributes": True}


# ── Production Progress Dashboard (Phase 11) ──────────────────────────────────

class ProductionDashboardRow(BaseModel):
    lot_id: UUID
    lot_number: str
    style_name: str | None
    customer_id: UUID | None
    customer_name: str | None = None
    status: str
    planned_qty: int
    produced_qty: int
    pending_qty: int
    rejected_qty: int
    rework_qty: int
    yield_pct: Decimal | None
    material_shortage_lines: int
    cost_planned: Decimal
    cost_actual: Decimal
    cost_variance_amount: Decimal
    dispatched_qty: Decimal
    returned_qty: Decimal
    undispatched_qty: Decimal


class ProductionDashboardTotals(BaseModel):
    lots: int
    planned_qty: int
    produced_qty: int
    pending_qty: int
    rejected_qty: int
    rework_qty: int
    material_shortage_lines: int
    cost_planned: Decimal
    cost_actual: Decimal
    cost_variance_amount: Decimal
    dispatched_qty: Decimal
    returned_qty: Decimal


class ProductionDashboardOut(BaseModel):
    rows: list[ProductionDashboardRow] = []
    totals: ProductionDashboardTotals
    lots_by_status: dict[str, int] = {}


class ProductionAuditLogOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    field_name: str | None
    old_value: str | None
    new_value: str | None
    notes: str | None
    changed_by: UUID | None
    changed_by_name: str | None = None
    changed_at: datetime
    model_config = {"from_attributes": True}
