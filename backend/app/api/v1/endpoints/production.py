"""Production module endpoints: styles, lots, stages, MIS, outputs."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import AuthUser, DBSession
from app.models.production import MaterialIssue, ProductionLot, ProductionOutput
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.production import (
    MaterialIssueCreate, MaterialIssueOut, MISItemOut,
    ProductionLotCreate, ProductionLotOut, ProductionLotUpdate,
    ProductionOutputCreate, ProductionOutputOut,
    StageCreate, StageEntryCreate, StageEntryOut, StageOut,
    StyleCreate, StyleOut,
    LotSizeOut,
)
from app.services.production import ProductionService

router = APIRouter(prefix="/production", tags=["production"])


def _lot_out(lot: ProductionLot) -> ProductionLotOut:
    return ProductionLotOut(
        id=lot.id, lot_number=lot.lot_number,
        style_id=lot.style_id,
        style_name=lot.style.name if lot.style else None,
        customer_id=lot.customer_id, sales_order_id=lot.sales_order_id,
        order_ref=lot.order_ref, planned_qty=lot.planned_qty, actual_qty=lot.actual_qty,
        delivery_date=lot.delivery_date, season=lot.season, target_sp=lot.target_sp,
        status=lot.status, notes=lot.notes, closed_at=lot.closed_at,
        sizes=[LotSizeOut.model_validate(s) for s in lot.sizes],
    )


def _mis_out(mis: MaterialIssue) -> MaterialIssueOut:
    return MaterialIssueOut(
        id=mis.id, issue_number=mis.issue_number,
        production_lot_id=mis.production_lot_id,
        lot_number=mis.production_lot.lot_number if mis.production_lot else None,
        stage_id=mis.stage_id, warehouse_id=mis.warehouse_id,
        issue_date=mis.issue_date, status=mis.status, notes=mis.notes,
        items=[MISItemOut.model_validate(i) for i in mis.items],
    )


def _output_out(o: ProductionOutput) -> ProductionOutputOut:
    return ProductionOutputOut(
        id=o.id, output_number=o.output_number,
        production_lot_id=o.production_lot_id,
        lot_number=o.production_lot.lot_number if o.production_lot else None,
        warehouse_id=o.warehouse_id, output_date=o.output_date,
        product_id=o.product_id, quantity=o.quantity,
        unit_id=o.unit_id, unit_cost=o.unit_cost, total_cost=o.total_cost,
        inv_transaction_id=o.inv_transaction_id,
    )


# ── Styles ────────────────────────────────────────────────────────────────────

@router.get("/styles")
async def list_styles(db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    styles = await svc.list_styles(user.company_id)
    return ApiResponse(success=True, data=[StyleOut.model_validate(s) for s in styles])


@router.post("/styles", status_code=201)
async def create_style(body: StyleCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    s = await svc.create_style(body, user.company_id)
    return ApiResponse(success=True, data=StyleOut.model_validate(s))


# ── Production Lots ───────────────────────────────────────────────────────────

@router.get("/lots")
async def list_lots(
    db: DBSession, user: AuthUser,
    status: str | None = None, page: int = 1, page_size: int = 50,
):
    user.require("production.view")
    svc = ProductionService(db)
    lots, total = await svc.list_lots(user.company_id, status=status, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_lot_out(l) for l in lots],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/lots", status_code=201)
async def create_lot(body: ProductionLotCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    try:
        lot = await svc.create_lot(body, user.company_id, user.user_id)
    except IntegrityError as exc:
        detail = str(exc.orig) if exc.orig else str(exc)
        if "lot_number" in detail or "unique" in detail.lower():
            raise HTTPException(409, "Lot number already exists for this company")
        raise HTTPException(422, "Invalid reference: style, customer, or sales order not found")
    return ApiResponse(success=True, data=_lot_out(lot))


@router.get("/lots/{lot_id}")
async def get_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    lot = await svc.get_lot(lot_id, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=_lot_out(lot))


@router.patch("/lots/{lot_id}")
async def update_lot(lot_id: UUID, body: ProductionLotUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    lot = await svc.update_lot(lot_id, body, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=_lot_out(lot))


class StatusBody(ProductionLotUpdate):
    status: str


@router.post("/lots/{lot_id}/status")
async def advance_lot_status(lot_id: UUID, body: StatusBody, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    lot = await svc.advance_lot_status(lot_id, user.company_id, body.status)
    if not lot:
        raise HTTPException(400, "Lot not found or invalid status transition")
    return ApiResponse(success=True, data=_lot_out(lot))


# ── Stages ────────────────────────────────────────────────────────────────────

@router.post("/lots/{lot_id}/stages", status_code=201)
async def add_stage(lot_id: UUID, body: StageCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    stage = await svc.add_stage(lot_id, body, user.company_id)
    return ApiResponse(success=True, data=StageOut.model_validate(stage))


@router.post("/stages/{stage_id}/entries", status_code=201)
async def add_stage_entry(stage_id: UUID, body: StageEntryCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    entry = await svc.add_stage_entry(stage_id, body, user.user_id)
    return ApiResponse(success=True, data=StageEntryOut.model_validate(entry))


# ── Material Issues (MIS) ─────────────────────────────────────────────────────

@router.get("/mis")
async def list_mis(
    db: DBSession, user: AuthUser,
    lot_id: UUID | None = None, page: int = 1, page_size: int = 50,
):
    user.require("production.view")
    svc = ProductionService(db)
    issues, total = await svc.list_mis(user.company_id, lot_id=lot_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_mis_out(m) for m in issues],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/mis", status_code=201)
async def create_mis(body: MaterialIssueCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    if not body.items:
        raise HTTPException(400, "MIS must have at least one item")
    svc = ProductionService(db)
    mis = await svc.create_mis(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_mis_out(mis))


@router.get("/mis/{mis_id}")
async def get_mis(mis_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    mis = await svc.get_mis(mis_id, user.company_id)
    if not mis:
        raise HTTPException(404, "Material issue not found")
    return ApiResponse(success=True, data=_mis_out(mis))


# ── Production Outputs ────────────────────────────────────────────────────────

@router.get("/outputs")
async def list_outputs(
    db: DBSession, user: AuthUser,
    lot_id: UUID | None = None, page: int = 1, page_size: int = 50,
):
    user.require("production.view")
    svc = ProductionService(db)
    outputs, total = await svc.list_outputs(user.company_id, lot_id=lot_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_output_out(o) for o in outputs],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/outputs", status_code=201)
async def create_output(body: ProductionOutputCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    output = await svc.create_output(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_output_out(output))
