from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class CompositionItemIn(BaseModel):
    fibre_name: str
    percentage: Decimal

    @field_validator("percentage")
    @classmethod
    def _pct_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") < v <= Decimal("100")):
            raise ValueError("percentage must be between 0 and 100")
        return v


class CompositionItemOut(BaseModel):
    id: UUID
    fibre_name: str
    percentage: Decimal
    model_config = {"from_attributes": True}


class FabricVariantIn(BaseModel):
    colour: Optional[str] = None
    dia_inches: Optional[Decimal] = None
    notes: Optional[str] = None


class FabricVariantOut(BaseModel):
    id: UUID
    colour: Optional[str] = None
    dia_inches: Optional[Decimal] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


class TrimVariantIn(BaseModel):
    colour: Optional[str] = None
    notes: Optional[str] = None


class TrimVariantOut(BaseModel):
    id: UUID
    colour: Optional[str] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Yarn ──────────────────────────────────────────────────────────────────────

class YarnCreate(BaseModel):
    lot_number: Optional[str] = None            # auto-generated if absent
    supplier_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    yarn_count: Optional[str] = None
    ply: Optional[str] = None
    mill: Optional[str] = None
    spinning_type: Optional[str] = None         # Ring / Open-end / Vortex
    treatment: Optional[str] = None             # Compact / Gassed / Mercerised
    colour: Optional[str] = None
    compositions: list[CompositionItemIn] = []
    bags: Optional[Decimal] = None
    kg_per_bag: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None         # rate per kg
    notes: Optional[str] = None
    # Inventory booking (optional)
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    transaction_date: Optional[date] = None


# ── Fabric ────────────────────────────────────────────────────────────────────

class FabricCreate(BaseModel):
    lot_number: Optional[str] = None
    supplier_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    construction: Optional[str] = None         # Knit / Woven / etc.
    gsm: Optional[Decimal] = None
    diameter_inches: Optional[Decimal] = None
    colour: Optional[str] = None
    finish: Optional[str] = None               # comma-sep or single value
    compositions: list[CompositionItemIn] = []
    split_by_colour: bool = False
    split_by_dia: bool = False
    fabric_variants: list[FabricVariantIn] = []
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None
    # Inventory booking (optional)
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    quantity: Optional[Decimal] = None
    transaction_date: Optional[date] = None


# ── Trims ─────────────────────────────────────────────────────────────────────

class TrimCreate(BaseModel):
    lot_number: Optional[str] = None
    trim_type: Optional[str] = None
    trim_unit: Optional[str] = None
    supplier_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    colour: Optional[str] = None
    split_by_colour: bool = False
    trim_variants: list[TrimVariantIn] = []
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None
    # Inventory booking (optional)
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    quantity: Optional[Decimal] = None
    transaction_date: Optional[date] = None


# ── Fabric Run ────────────────────────────────────────────────────────────────

class FabricRunCreate(BaseModel):
    run_number: Optional[str] = None
    construction: Optional[str] = None
    input_lot_id: Optional[UUID] = None
    input_qty: Optional[Decimal] = None
    machine: Optional[str] = None
    started_at: Optional[date] = None
    notes: Optional[str] = None


# ── Output schemas ────────────────────────────────────────────────────────────

class LotOut(BaseModel):
    id: UUID
    company_id: UUID
    lot_number: str
    material_type: str
    supplier_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    yarn_count: Optional[str] = None
    ply: Optional[str] = None
    mill: Optional[str] = None
    fibre_type: Optional[str] = None
    blend_composition: Optional[str] = None
    spinning_type: Optional[str] = None
    treatment: Optional[str] = None
    construction: Optional[str] = None
    gsm: Optional[Decimal] = None
    diameter_inches: Optional[Decimal] = None
    colour: Optional[str] = None
    finish: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    bags: Optional[Decimal] = None
    kg_per_bag: Optional[Decimal] = None
    trim_type: Optional[str] = None
    trim_unit: Optional[str] = None
    split_by_colour: bool = False
    split_by_dia: bool = False
    notes: Optional[str] = None
    compositions: list[CompositionItemOut] = []
    fabric_variants: list[FabricVariantOut] = []
    trim_variants: list[TrimVariantOut] = []
    model_config = {"from_attributes": True}


class FabricRunOut(BaseModel):
    id: UUID
    company_id: UUID
    run_number: str
    construction: Optional[str] = None
    input_lot_id: Optional[UUID] = None
    input_qty: Optional[Decimal] = None
    output_qty: Optional[Decimal] = None
    wastage_qty: Optional[Decimal] = None
    wastage_pct: Optional[Decimal] = None
    output_lot_id: Optional[UUID] = None
    machine: Optional[str] = None
    status: str
    started_at: Optional[date] = None
    closed_at: Optional[date] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}
