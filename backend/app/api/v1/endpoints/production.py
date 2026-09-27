"""Production module endpoints: styles, lots, stages, MIS, outputs."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import AuthUser, DBSession
from app.models.production import MaterialIssue, ProductionLot, ProductionOutput, ProductionStage, ProductionStageChallan
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.production import (
    FabricProcessingComplete, FabricProcessingCreate, FabricProcessingOut, FabricProcessingUpdate,
    InternalWorkerCreate, InternalWorkerOut,
    LotAdditionalCostCreate, LotAdditionalCostOut, LotAdditionalCostUpdate,
    MaterialIssueCreate, MaterialIssueOut, MISItemOut,
    ProductionLotCreate, ProductionLotOut, ProductionLotUpdate,
    ProductionOutputCreate, ProductionOutputOut,
    StageChallanBillUpdate, StageChallanCreate, StageChallanOut, StageChallanReceive,
    StageCreate, StageEntryCreate, StageEntryOut, StageOut, StageUpdate,
    StyleCreate, StyleOut, StyleDetailOut,
    LotSizeOut,
)
from app.services.production import (
    ProductionService, QuantityValidationError,
    _stage_accepted_qty, compute_lot_cost_summary, compute_target_price_check,
)
from app.services.production_report import build_lot_report_data, render_lot_report_pdf, report_filename

router = APIRouter(prefix="/production", tags=["production"])


def _challan_out(c: ProductionStageChallan) -> StageChallanOut:
    out = StageChallanOut.model_validate(c)
    out.pending_qty = c.out_qty - (c.in_qty or 0) - (c.rejected_qty or 0)
    return out


def _stage_out(s: ProductionStage) -> StageOut:
    out = StageOut.model_validate(s)
    out.accepted_qty = _stage_accepted_qty(s)
    out.challans = [_challan_out(c) for c in sorted(s.challans, key=lambda c: c.out_date)]
    return out


async def _lot_out(lot: ProductionLot, svc: ProductionService) -> ProductionLotOut:
    selling_prices = await svc.resolve_selling_prices(lot)
    return ProductionLotOut(
        id=lot.id, lot_number=lot.lot_number,
        style_id=lot.style_id,
        style_name=lot.style.name if lot.style else None,
        customer_id=lot.customer_id, sales_order_id=lot.sales_order_id,
        order_ref=lot.order_ref, planned_qty=lot.planned_qty, actual_qty=lot.actual_qty,
        colour_id=lot.colour_id, planned_weight_kg=lot.planned_weight_kg,
        actual_weight_kg=lot.actual_weight_kg,
        delivery_date=lot.delivery_date, season=lot.season, target_sp=lot.target_sp,
        actual_selling_price=lot.actual_selling_price,
        status=lot.status, notes=lot.notes,
        final_output_unit=lot.final_output_unit, pieces_per_box=lot.pieces_per_box, style_version=lot.style_version,
        closed_at=lot.closed_at,
        sizes=[LotSizeOut.model_validate(s) for s in lot.sizes],
        stages=[_stage_out(s) for s in sorted(lot.stages, key=lambda s: s.created_at)],
        additional_costs=[LotAdditionalCostOut.model_validate(a) for a in lot.additional_costs],
        fabric_processing=[FabricProcessingOut.model_validate(f) for f in sorted(lot.fabric_processing, key=lambda f: f.created_at)],
        cost_summary=compute_lot_cost_summary(lot, selling_prices),
    )


def _style_detail_out(s) -> StyleDetailOut:
    out = StyleDetailOut.model_validate(s)
    out.target_price_check = compute_target_price_check(s)
    return out


def _mis_item_out(item) -> MISItemOut:
    out = MISItemOut.model_validate(item)
    if item.planned_qty is not None and item.issued_qty > item.planned_qty:
        out.excess_qty = item.issued_qty - item.planned_qty   # §47.4 — excess must stay visible
    return out


def _mis_out(mis: MaterialIssue) -> MaterialIssueOut:
    return MaterialIssueOut(
        id=mis.id, issue_number=mis.issue_number,
        production_lot_id=mis.production_lot_id,
        lot_number=mis.production_lot.lot_number if mis.production_lot else None,
        stage_id=mis.stage_id, warehouse_id=mis.warehouse_id,
        issue_date=mis.issue_date, status=mis.status, notes=mis.notes,
        items=[_mis_item_out(i) for i in mis.items],
    )


def _output_out(o: ProductionOutput) -> ProductionOutputOut:
    return ProductionOutputOut(
        id=o.id, output_number=o.output_number,
        production_lot_id=o.production_lot_id,
        lot_number=o.production_lot.lot_number if o.production_lot else None,
        warehouse_id=o.warehouse_id, output_date=o.output_date,
        product_id=o.product_id, quantity=o.quantity, rejected_qty=o.rejected_qty,
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
    s = await svc.create_style(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_style_detail_out(s))


@router.get("/styles/{style_id}")
async def get_style(style_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    s = await svc.get_style(style_id, user.company_id)
    if not s:
        raise HTTPException(404, "Style not found")
    return ApiResponse(success=True, data=_style_detail_out(s))


@router.patch("/styles/{style_id}")
async def update_style(style_id: UUID, body: StyleCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    s = await svc.update_style(style_id, body, user.company_id)
    if not s:
        raise HTTPException(404, "Style not found")
    return ApiResponse(success=True, data=_style_detail_out(s), message="Style updated")


@router.post("/styles/{style_id}/clone", status_code=201)
async def clone_style(style_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    s = await svc.clone_style(style_id, user.company_id, user.user_id)
    if not s:
        raise HTTPException(404, "Style not found")
    return ApiResponse(success=True, data=_style_detail_out(s), message="Style cloned")


# ── Production Lots ───────────────────────────────────────────────────────────

@router.get("/lots")
async def list_lots(
    db: DBSession, user: AuthUser,
    status: str | None = None, page: int = 1, page_size: int = 50,
):
    user.require("production.view")
    svc = ProductionService(db)
    lots, total = await svc.list_lots(user.company_id, status=status, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[await _lot_out(l, svc) for l in lots],
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
    return ApiResponse(success=True, data=await _lot_out(lot, svc))


@router.get("/lots/{lot_id}")
async def get_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    lot = await svc.get_lot(lot_id, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=await _lot_out(lot, svc))


@router.patch("/lots/{lot_id}")
async def update_lot(lot_id: UUID, body: ProductionLotUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    lot = await svc.update_lot(lot_id, body, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=await _lot_out(lot, svc))


class StatusBody(ProductionLotUpdate):
    status: str


@router.post("/lots/{lot_id}/status")
async def advance_lot_status(lot_id: UUID, body: StatusBody, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    lot = await svc.advance_lot_status(lot_id, user.company_id, body.status)
    if not lot:
        raise HTTPException(400, "Lot not found or invalid status transition")
    return ApiResponse(success=True, data=await _lot_out(lot, svc))


@router.post("/lots/{lot_id}/reopen")
async def reopen_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        lot = await svc.reopen_lot(lot_id, user.company_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=await _lot_out(lot, svc), message="Lot reopened")


@router.delete("/lots/{lot_id}")
async def delete_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        deleted = await svc.delete_lot(lot_id, user.company_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not deleted:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, message="Lot deleted")


@router.get("/lots/{lot_id}/report.pdf")
async def get_lot_report_pdf(lot_id: UUID, db: DBSession, user: AuthUser, preview: bool = False):
    user.require("production.view")
    svc = ProductionService(db)
    lot = await svc.get_lot(lot_id, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    report_data = await build_lot_report_data(db, svc, lot, user.company_id)
    pdf_bytes = render_lot_report_pdf(report_data)
    filename = report_filename(lot, lot.style.name if lot.style else None)
    disposition = "inline" if preview else "attachment"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


# ── Stages ────────────────────────────────────────────────────────────────────

@router.post("/lots/{lot_id}/stages", status_code=201)
async def add_stage(lot_id: UUID, body: StageCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        stage = await svc.add_stage(lot_id, body, user.company_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not stage:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=_stage_out(stage), message="Stage added")


@router.patch("/stages/{stage_id}")
async def update_stage(stage_id: UUID, body: StageUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        stage = await svc.update_stage(stage_id, body, user.company_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not stage:
        raise HTTPException(404, "Stage not found")
    return ApiResponse(success=True, data=_stage_out(stage), message="Stage updated")


@router.post("/lots/{lot_id}/additional-costs", status_code=201)
async def add_lot_additional_cost(lot_id: UUID, body: LotAdditionalCostCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    cost = await svc.add_lot_additional_cost(lot_id, body, user.company_id)
    if not cost:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=LotAdditionalCostOut.model_validate(cost), message="Cost added")


@router.delete("/lots/additional-costs/{cost_id}")
async def delete_lot_additional_cost(cost_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    if not await svc.delete_lot_additional_cost(cost_id, user.company_id):
        raise HTTPException(404, "Additional cost not found")
    return ApiResponse(success=True, message="Cost removed")


@router.patch("/lots/additional-costs/{cost_id}")
async def update_lot_additional_cost(cost_id: UUID, body: LotAdditionalCostUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    cost = await svc.update_lot_additional_cost(cost_id, body, user.company_id)
    if not cost:
        raise HTTPException(404, "Additional cost not found")
    return ApiResponse(success=True, data=LotAdditionalCostOut.model_validate(cost), message="Additional cost updated")


@router.post("/stages/{stage_id}/entries", status_code=201)
async def add_stage_entry(stage_id: UUID, body: StageEntryCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        entry = await svc.add_stage_entry(stage_id, body, user.user_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    return ApiResponse(success=True, data=StageEntryOut.model_validate(entry))


# ── Stage Challans (Job Work OUT/IN) ───────────────────────────────────────────

@router.post("/stages/{stage_id}/challans", status_code=201)
async def create_challan(stage_id: UUID, body: StageChallanCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        challan = await svc.create_challan(stage_id, body, user.company_id, user.user_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not challan:
        raise HTTPException(404, "Stage not found")
    return ApiResponse(success=True, data=_challan_out(challan), message="Challan created")


@router.patch("/stages/challans/{challan_id}/receive")
async def receive_challan(challan_id: UUID, body: StageChallanReceive, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        challan = await svc.receive_challan(challan_id, body, user.company_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not challan:
        raise HTTPException(404, "Challan not found")
    return ApiResponse(success=True, data=_challan_out(challan), message="Challan received")


@router.patch("/stages/challans/{challan_id}/bill")
async def update_challan_bill(challan_id: UUID, body: StageChallanBillUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    challan = await svc.update_challan_bill(challan_id, body, user.company_id)
    if not challan:
        raise HTTPException(404, "Challan not found")
    return ApiResponse(success=True, data=_challan_out(challan), message="Bill status updated")


# ── Internal Workers ────────────────────────────────────────────────────────────

@router.get("/workers")
async def list_workers(db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    workers = await svc.list_workers(user.company_id)
    return ApiResponse(success=True, data=[InternalWorkerOut.model_validate(w) for w in workers])


@router.post("/workers", status_code=201)
async def create_worker(body: InternalWorkerCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    worker = await svc.create_worker(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=InternalWorkerOut.model_validate(worker), message="Worker added")


# ── Fabric Processing (dyeing/printing) ────────────────────────────────────────

@router.post("/lots/{lot_id}/fabric-processing", status_code=201)
async def create_fabric_processing(lot_id: UUID, body: FabricProcessingCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    entry = await svc.create_fabric_processing(lot_id, body, user.company_id, user.user_id)
    if not entry:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=FabricProcessingOut.model_validate(entry), message="Fabric processing started")


@router.patch("/fabric-processing/{entry_id}/complete")
async def complete_fabric_processing(entry_id: UUID, body: FabricProcessingComplete, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    entry = await svc.complete_fabric_processing(entry_id, body, user.company_id)
    if not entry:
        raise HTTPException(404, "Fabric processing entry not found")
    return ApiResponse(success=True, data=FabricProcessingOut.model_validate(entry), message="Fabric processing completed")


@router.patch("/fabric-processing/{entry_id}")
async def update_fabric_processing(entry_id: UUID, body: FabricProcessingUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    entry = await svc.update_fabric_processing(entry_id, body, user.company_id)
    if not entry:
        raise HTTPException(404, "Fabric processing entry not found")
    return ApiResponse(success=True, data=FabricProcessingOut.model_validate(entry), message="Fabric processing updated")


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
