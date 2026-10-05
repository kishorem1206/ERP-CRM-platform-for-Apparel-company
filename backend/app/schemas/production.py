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


class StyleYarnIn(BaseModel):
    yarn_name: str
    lot_id: UUID | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    notes: str | None = None


class StyleYarnOut(BaseModel):
    id: UUID
    yarn_name: str
    lot_id: UUID | None
    quantity: Decimal | None
    unit: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleFabricIn(BaseModel):
    fabric_name: str
    lot_id: UUID | None = None
    consumption: Decimal | None = None
    unit: str | None = None
    excess_pct: Decimal | None = None
    gsm: Decimal | None = None
    dyeing_rate: Decimal | None = None
    printing_rate: Decimal | None = None
    notes: str | None = None


class StyleFabricOut(BaseModel):
    id: UUID
    fabric_name: str
    lot_id: UUID | None
    consumption: Decimal | None
    unit: str | None
    excess_pct: Decimal | None
    gsm: Decimal | None
    dyeing_rate: Decimal | None
    printing_rate: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


class StyleSubProcessIn(BaseModel):
    seq: int = 0
    name: str
    notes: str | None = None


class StyleSubProcessOut(BaseModel):
    id: UUID
    seq: int
    name: str
    notes: str | None
    model_config = {"from_attributes": True}


class StyleProcessIn(BaseModel):
    seq: int = 0
    process_name: str
    process_master_id: UUID | None = None
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
    quantity: Decimal | None = None
    unit: str | None = None
    excess_pct: Decimal | None = None
    consumption_stage: str | None = None
    notes: str | None = None


class StylePackingMaterialOut(BaseModel):
    id: UUID
    material_name: str
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
    sizes: list[StyleSizeIn] = []
    colours: list[StyleColourIn] = []
    yarns: list[StyleYarnIn] = []
    fabrics: list[StyleFabricIn] = []
    processes: list[StyleProcessIn] = []
    trims: list[StyleTrimIn] = []
    packing_materials: list[StylePackingMaterialIn] = []
    additional_costs: list[StyleAdditionalCostIn] = []


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
    hsn_id: UUID | None = None
    gst_rate: Decimal | None = None
    sizes: list[StyleSizeOut] = []
    colours: list[StyleColourOut] = []
    yarns: list[StyleYarnOut] = []
    fabrics: list[StyleFabricOut] = []
    processes: list[StyleProcessOut] = []
    trims: list[StyleTrimOut] = []
    packing_materials: list[StylePackingMaterialOut] = []
    additional_costs: list[StyleAdditionalCostOut] = []
    target_price_check: TargetPriceCheckOut | None = None
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
    colour_id: UUID | None = None
    planned_weight_kg: Decimal | None = None
    delivery_date: date | None = None
    season: str | None = None
    target_sp: Decimal | None = None
    pieces_per_box: int | None = None   # defaults to the Style's
    notes: str | None = None
    sizes: list[LotSizeCreate] = []
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
    notes: str | None = None


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
    entries: list[StageEntryOut] = []
    challans: list[StageChallanOut] = []
    model_config = {"from_attributes": True}


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


class LotPackingMaterialOut(BaseModel):
    id: UUID
    style_packing_material_id: UUID | None
    material_name: str
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


class MaterialIssueOut(BaseModel):
    id: UUID
    issue_number: str
    production_lot_id: UUID
    lot_number: str | None = None
    stage_id: UUID | None
    warehouse_id: UUID
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
    output_date: date
    product_id: UUID
    variant_id: UUID | None = None
    quantity: Decimal
    rejected_qty: Decimal | None
    unit_id: UUID
    unit_cost: Decimal
    total_cost: Decimal
    inv_transaction_id: UUID | None
    model_config = {"from_attributes": True}
