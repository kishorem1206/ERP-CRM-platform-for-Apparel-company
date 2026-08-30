from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ReceiveParams(BaseModel):
    company_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    lot_id: UUID | None = None
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal
    material_type: str = "finished_good"
    transaction_date: date
    reference_type: str | None = None
    reference_id: UUID | None = None
    notes: str | None = None


class IssueParams(BaseModel):
    company_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    lot_id: UUID | None = None
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal
    material_type: str = "finished_good"
    transaction_date: date
    reference_type: str | None = None
    reference_id: UUID | None = None
    notes: str | None = None


class TransferParams(BaseModel):
    company_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal
    material_type: str = "finished_good"
    transaction_date: date
    notes: str | None = None


class AdjustParams(BaseModel):
    company_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    new_quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal
    material_type: str = "finished_good"
    transaction_date: date
    reason: str


# ── API-level request schemas ──────────────────────────────────────────────────

class StockInRequest(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")
    material_type: str = "raw_material"
    transaction_date: date
    notes: str | None = None


class StockOutRequest(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")
    material_type: str = "raw_material"
    transaction_date: date
    notes: str | None = None


class TransferRequest(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")
    material_type: str = "raw_material"
    transaction_date: date
    notes: str | None = None


class AdjustRequest(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    warehouse_id: UUID
    new_quantity: Decimal
    unit_id: UUID
    unit_cost: Decimal = Decimal("0")
    material_type: str = "raw_material"
    transaction_date: date
    reason: str


# ── Response schemas ───────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: UUID
    transaction_type: str
    reference_type: str | None
    product_id: UUID
    variant_id: UUID | None
    warehouse_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    direction: int
    transaction_date: date
    notes: str | None
    material_type: str
    model_config = {"from_attributes": True}


class StockBalanceRow(BaseModel):
    product_id: str
    product_name: str
    product_type: str
    warehouse_id: str
    warehouse_name: str
    unit_symbol: str
    balance: Decimal
