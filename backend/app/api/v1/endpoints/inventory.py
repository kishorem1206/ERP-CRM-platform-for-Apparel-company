"""Inventory transactions UI: stock-in, stock-out, transfer, adjust, transaction log, balance."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.v1.deps import AuthUser, DBSession
from app.domain.business_rules import BusinessRulesError
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.inventory import (
    AdjustParams, AdjustRequest,
    IssueParams, StockOutRequest,
    ReceiveParams, StockInRequest,
    StockBalanceRow, TransactionOut,
    TransferParams, TransferRequest,
)
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ── Manual Stock-In ────────────────────────────────────────────────────────────

@router.post("/stock-in", status_code=201)
async def stock_in(body: StockInRequest, db: DBSession, user: AuthUser):
    user.require("inventory.create")
    svc = InventoryService(db)
    tx = await svc.receive(
        ReceiveParams(
            company_id=user.company_id,
            product_id=body.product_id,
            variant_id=body.variant_id,
            warehouse_id=body.warehouse_id,
            quantity=body.quantity,
            unit_id=body.unit_id,
            unit_cost=body.unit_cost,
            material_type=body.material_type,
            transaction_date=body.transaction_date,
            reference_type="manual",
            notes=body.notes,
        ),
        user_id=user.user_id,
    )
    return ApiResponse(success=True, data=TransactionOut.model_validate(tx))


# ── Manual Stock-Out ───────────────────────────────────────────────────────────

@router.post("/stock-out", status_code=201)
async def stock_out(body: StockOutRequest, db: DBSession, user: AuthUser):
    user.require("inventory.create")
    svc = InventoryService(db)
    try:
        tx = await svc.issue(
            IssueParams(
                company_id=user.company_id,
                product_id=body.product_id,
                variant_id=body.variant_id,
                warehouse_id=body.warehouse_id,
                quantity=body.quantity,
                unit_id=body.unit_id,
                unit_cost=body.unit_cost,
                material_type=body.material_type,
                transaction_date=body.transaction_date,
                reference_type="manual",
                notes=body.notes,
            ),
            user_id=user.user_id,
        )
    except BusinessRulesError as e:
        raise HTTPException(422, str(e))
    return ApiResponse(success=True, data=TransactionOut.model_validate(tx))


# ── Transfer ───────────────────────────────────────────────────────────────────

@router.post("/transfer", status_code=201)
async def transfer(body: TransferRequest, db: DBSession, user: AuthUser):
    user.require("inventory.create")
    if body.from_warehouse_id == body.to_warehouse_id:
        raise HTTPException(400, "Source and destination warehouse must differ")
    svc = InventoryService(db)
    try:
        out_tx, in_tx = await svc.transfer(
            TransferParams(
                company_id=user.company_id,
                product_id=body.product_id,
                variant_id=body.variant_id,
                from_warehouse_id=body.from_warehouse_id,
                to_warehouse_id=body.to_warehouse_id,
                quantity=body.quantity,
                unit_id=body.unit_id,
                unit_cost=body.unit_cost,
                material_type=body.material_type,
                transaction_date=body.transaction_date,
                notes=body.notes,
            ),
            user_id=user.user_id,
        )
    except BusinessRulesError as e:
        raise HTTPException(422, str(e))
    return ApiResponse(success=True, data={
        "transfer_out": TransactionOut.model_validate(out_tx),
        "transfer_in": TransactionOut.model_validate(in_tx),
    })


# ── Adjustment ─────────────────────────────────────────────────────────────────

@router.post("/adjust", status_code=201)
async def adjust(body: AdjustRequest, db: DBSession, user: AuthUser):
    user.require("inventory.create")
    svc = InventoryService(db)
    tx = await svc.adjust(
        AdjustParams(
            company_id=user.company_id,
            product_id=body.product_id,
            variant_id=body.variant_id,
            warehouse_id=body.warehouse_id,
            new_quantity=body.new_quantity,
            unit_id=body.unit_id,
            unit_cost=body.unit_cost,
            material_type=body.material_type,
            transaction_date=body.transaction_date,
            reason=body.reason,
        ),
        user_id=user.user_id,
    )
    if tx is None:
        return ApiResponse(success=True, message="No change — quantity already matches", data=None)
    return ApiResponse(success=True, data=TransactionOut.model_validate(tx))


# ── Transaction Log ────────────────────────────────────────────────────────────

@router.get("/transactions")
async def list_transactions(
    db: DBSession, user: AuthUser,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    transaction_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("inventory.view")
    svc = InventoryService(db)
    rows, total = await svc.list_transactions(
        user.company_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        success=True,
        data=[TransactionOut.model_validate(r) for r in rows],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


# ── Stock Balance Report ───────────────────────────────────────────────────────

@router.get("/balance")
async def stock_balance(db: DBSession, user: AuthUser):
    user.require("inventory.view")
    svc = InventoryService(db)
    rows = await svc.get_stock_balance(user.company_id)
    return ApiResponse(success=True, data=[StockBalanceRow(**r) for r in rows])
