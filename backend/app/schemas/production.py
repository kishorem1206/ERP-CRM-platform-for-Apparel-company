"""Pydantic schemas for the Production module."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


# ── Style ─────────────────────────────────────────────────────────────────────

class StyleCreate(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    garment_type: str | None = None
    gender: str | None = None
    season: str | None = None


class StyleOut(BaseModel):
    id: UUID
    name: str
    code: str | None
    garment_type: str | None
    gender: str | None
    season: str | None
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


class ProductionLotCreate(BaseModel):
    lot_number: str | None = None
    style_id: UUID | None = None
    customer_id: UUID | None = None
    sales_order_id: UUID | None = None
    order_ref: str | None = None
    planned_qty: int
    delivery_date: date | None = None
    season: str | None = None
    target_sp: Decimal | None = None
    notes: str | None = None
    sizes: list[LotSizeCreate] = []


class ProductionLotUpdate(BaseModel):
    delivery_date: date | None = None
    season: str | None = None
    target_sp: Decimal | None = None
    notes: str | None = None


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
    delivery_date: date | None
    season: str | None
    target_sp: Decimal | None
    status: str
    notes: str | None
    closed_at: datetime | None
    sizes: list[LotSizeOut] = []
    model_config = {"from_attributes": True}


# ── Production Stage ──────────────────────────────────────────────────────────

class StageCreate(BaseModel):
    stage_type: str
    stage_name: str
    planned_qty: int | None = None
    vendor_id: UUID | None = None
    rate_per_pc: Decimal | None = None
    notes: str | None = None

    @field_validator("stage_type")
    @classmethod
    def validate_stage_type(cls, v: str) -> str:
        allowed = {"cutting", "making", "finishing", "qc", "packing", "dispatch"}
        if v not in allowed:
            raise ValueError(f"stage_type must be one of {allowed}")
        return v


class StageOut(BaseModel):
    id: UUID
    stage_type: str
    stage_name: str
    planned_qty: int | None
    input_qty: int
    output_qty: int
    rejected_qty: int
    rework_qty: int
    status: str
    vendor_id: UUID | None
    rate_per_pc: Decimal | None
    bill_amount: Decimal | None
    notes: str | None
    model_config = {"from_attributes": True}


# ── Stage Entry ───────────────────────────────────────────────────────────────

class StageEntryCreate(BaseModel):
    entry_date: date
    pieces_in: int = 0
    pieces_out: int = 0
    rejected: int = 0
    operator: str | None = None
    machine: str | None = None
    notes: str | None = None


class StageEntryOut(BaseModel):
    id: UUID
    entry_date: date
    pieces_in: int
    pieces_out: int
    rejected: int
    operator: str | None
    machine: str | None
    notes: str | None
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
    planned_qty: Decimal | None
    issued_qty: Decimal
    unit_id: UUID
    unit_cost: Decimal
    total_cost: Decimal
    inv_transaction_id: UUID | None
    model_config = {"from_attributes": True}


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
    quantity: Decimal
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
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal
    total_cost: Decimal
    inv_transaction_id: UUID | None
    model_config = {"from_attributes": True}
