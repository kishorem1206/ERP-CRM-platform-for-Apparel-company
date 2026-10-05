"""Production module endpoints: styles, lots, stages, MIS, outputs."""
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import AuthUser, DBSession
from app.models.company import Company
from app.models.master import Product, Unit
from app.models.production import InternalWorker, MaterialIssue, ProductionLot, ProductionOutput, ProductionStage, ProductionStageChallan
from app.models.purchase import Vendor
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.production import (
    FabricProcessingComplete, FabricProcessingCreate, FabricProcessingOut, FabricProcessingUpdate,
    InternalWorkerCreate, InternalWorkerOut,
    LotAdditionalCostCreate, LotAdditionalCostOut, LotAdditionalCostUpdate,
    LotPackingActualUpdate, LotPackingMaterialOut, LotTrimActualUpdate, LotTrimOut,
    MaterialIssueCreate, MaterialIssueOut, MISItemOut, MISItemReturnUpdate,
    ProductionLotCreate, ProductionLotOut, ProductionLotUpdate,
    ProductionOutputCreate, ProductionOutputOut,
    SizeChartCreate, SizeChartOut,
    StageChallanBillUpdate, StageChallanCreate, StageChallanOut, StageChallanReceive,
    StageCreate, StageEntryCreate, StageEntryOut, StageOut, StageUpdate,
    StyleCreate, StyleOut, StyleDetailOut,
    LotSizeOut,
)
from app.services.production import (
    DEFAULT_WASTAGE_PCT, ProductionService, QuantityValidationError,
    _stage_accepted_qty, compute_lot_cost_summary, compute_target_price_check,
)
from app.services.delivery_challan import delivery_challan_filename, render_delivery_challan_pdf
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

    if s.input_weight_kg is not None:
        tolerance_pct = s.tolerance_pct if s.tolerance_pct is not None else DEFAULT_WASTAGE_PCT
        expected_output_kg = s.input_weight_kg * (1 - tolerance_pct / 100)
        out.permitted_tolerance_kg = s.input_weight_kg * tolerance_pct / 100
        if s.output_weight_kg is not None:
            out.variance_kg = s.output_weight_kg - expected_output_kg
            out.within_tolerance = out.variance_kg >= 0
            if s.output_qty > 0:
                out.weight_per_piece = s.output_weight_kg / s.output_qty
                if s.rate_per_pc is not None:
                    out.effective_rate_per_kg = s.rate_per_pc * (Decimal(s.output_qty) / s.output_weight_kg)

    return out


async def _lot_out(lot: ProductionLot, svc: ProductionService) -> ProductionLotOut:
    selling_prices = await svc.resolve_selling_prices(lot)
    boxes_required = ceil(lot.actual_qty / lot.pieces_per_box) if lot.pieces_per_box else None
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
        trims=[LotTrimOut.model_validate(t) for t in lot.trims],
        packing_materials=[LotPackingMaterialOut.model_validate(p) for p in lot.packing_materials],
        boxes_required=boxes_required,
        fabric_blockers=await svc.fabric_blockers(lot),
        fabric_processing=[FabricProcessingOut.model_validate(f) for f in sorted(lot.fabric_processing, key=lambda f: f.created_at)],
        cost_summary=compute_lot_cost_summary(lot, selling_prices),
    )


def _style_detail_out(s) -> StyleDetailOut:
    out = StyleDetailOut.model_validate(s)
    out.target_price_check = compute_target_price_check(s)
    if s.product:
        out.product_code = s.product.code
        if s.product.hsn:
            out.hsn_id = s.product.hsn.id
            out.gst_rate = s.product.hsn.gst_rate
    return out


async def _mis_item_out(db: DBSession, item) -> MISItemOut:
    out = MISItemOut.model_validate(item)
    if item.planned_qty is not None and item.issued_qty > item.planned_qty:
        out.excess_qty = item.issued_qty - item.planned_qty   # §47.4 — excess must stay visible
    out.product_name = (await db.execute(select(Product.name).where(Product.id == item.product_id))).scalar_one_or_none()
    out.unit_abbreviation = (await db.execute(select(Unit.abbreviation).where(Unit.id == item.unit_id))).scalar_one_or_none()
    return out


async def _mis_out(db: DBSession, mis: MaterialIssue) -> MaterialIssueOut:
    return MaterialIssueOut(
        id=mis.id, issue_number=mis.issue_number,
        production_lot_id=mis.production_lot_id,
        lot_number=mis.production_lot.lot_number if mis.production_lot else None,
        stage_id=mis.stage_id, warehouse_id=mis.warehouse_id,
        issue_date=mis.issue_date, status=mis.status, notes=mis.notes,
        items=[await _mis_item_out(db, i) for i in mis.items],
    )


def _output_out(o: ProductionOutput) -> ProductionOutputOut:
    return ProductionOutputOut(
        id=o.id, output_number=o.output_number,
        production_lot_id=o.production_lot_id,
        lot_number=o.production_lot.lot_number if o.production_lot else None,
        warehouse_id=o.warehouse_id, output_date=o.output_date,
        product_id=o.product_id, variant_id=o.variant_id, quantity=o.quantity, rejected_qty=o.rejected_qty,
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
    s = await svc.update_style(style_id, body, user.company_id, user.user_id)
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


# ── Size Chart Master ─────────────────────────────────────────────────────────

@router.get("/size-charts")
async def list_size_charts(db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    charts = await svc.list_size_charts(user.company_id)
    return ApiResponse(success=True, data=[SizeChartOut.model_validate(c) for c in charts])


@router.post("/size-charts", status_code=201)
async def create_size_chart(body: SizeChartCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    chart = await svc.create_size_chart(body, user.company_id)
    return ApiResponse(success=True, data=SizeChartOut.model_validate(chart), message="Size chart created")


@router.patch("/size-charts/{chart_id}")
async def update_size_chart(chart_id: UUID, body: SizeChartCreate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    chart = await svc.update_size_chart(chart_id, body, user.company_id)
    if not chart:
        raise HTTPException(404, "Size chart not found")
    return ApiResponse(success=True, data=SizeChartOut.model_validate(chart), message="Size chart updated")


@router.delete("/size-charts/{chart_id}")
async def delete_size_chart(chart_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.delete")
    svc = ProductionService(db)
    try:
        deleted = await svc.delete_size_chart(chart_id, user.company_id)
    except IntegrityError:
        raise HTTPException(409, "Cannot delete — this size chart is used by existing styles")
    if not deleted:
        raise HTTPException(404, "Size chart not found")
    return ApiResponse(success=True, message="Size chart deleted")


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


@router.patch("/lots/trims/{trim_id}")
async def update_lot_trim(trim_id: UUID, body: LotTrimActualUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    trim = await svc.update_lot_trim_actual(trim_id, body, user.company_id)
    if not trim:
        raise HTTPException(404, "Lot trim not found")
    return ApiResponse(success=True, data=LotTrimOut.model_validate(trim), message="Trim actual quantity updated")


@router.patch("/lots/packing/{packing_id}")
async def update_lot_packing(packing_id: UUID, body: LotPackingActualUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    packing = await svc.update_lot_packing_actual(packing_id, body, user.company_id)
    if not packing:
        raise HTTPException(404, "Lot packing material not found")
    return ApiResponse(success=True, data=LotPackingMaterialOut.model_validate(packing), message="Packing actual quantity updated")


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


@router.get("/stages/challans/{challan_id}/delivery-challan.pdf")
async def get_delivery_challan_pdf(challan_id: UUID, db: DBSession, user: AuthUser, preview: bool = False):
    """Printable Delivery Challan (ERP Upgrade §17), generated server-side
    from the existing job-work challan record - no second source of truth."""
    user.require("production.view")
    svc = ProductionService(db)
    challan = await svc.get_challan_for_document(challan_id, user.company_id)
    if not challan:
        raise HTTPException(404, "Challan not found")

    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()

    to_name, to_type = None, None
    if challan.vendor_id:
        vendor = (await db.execute(select(Vendor).where(Vendor.id == challan.vendor_id))).scalar_one_or_none()
        to_name, to_type = (vendor.name if vendor else None), "Vendor"
    elif challan.worker_id:
        worker = (await db.execute(select(InternalWorker).where(InternalWorker.id == challan.worker_id))).scalar_one_or_none()
        to_name, to_type = (worker.name if worker else None), "Internal Worker"

    lot = challan.stage.production_lot
    style = lot.style if lot else None
    product = style.product if style else None
    hsn = product.hsn if product else None

    value, value_estimated = challan.bill_amount, False
    if value is None and challan.stage.rate_per_pc is not None:
        value = challan.stage.rate_per_pc * challan.out_qty
        value_estimated = True

    challan_dict = {
        "challan_number": challan.challan_number, "out_date": str(challan.out_date),
        "status": challan.status, "in_date": str(challan.in_date) if challan.in_date else None,
        "in_qty": challan.in_qty, "rejected_qty": challan.rejected_qty,
    }
    item_dict = {
        "style_name": style.name if style else None,
        "process_name": challan.stage.stage_name,
        "lot_number": lot.lot_number if lot else None,
        "quantity": challan.out_qty,
        "hsn": hsn.hsn if hsn else None,
        "value": float(value) if value is not None else None,
        "value_estimated": value_estimated,
    }

    pdf_bytes = render_delivery_challan_pdf(
        company_name=company.name if company else None,
        challan=challan_dict,
        to_party={"name": to_name, "type": to_type},
        item=item_dict,
    )
    filename = delivery_challan_filename(challan.challan_number)
    disposition = "inline" if preview else "attachment"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


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
    return ApiResponse(success=True, data=[await _mis_out(db, m) for m in issues],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/mis", status_code=201)
async def create_mis(body: MaterialIssueCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    if not body.items:
        raise HTTPException(400, "MIS must have at least one item")
    svc = ProductionService(db)
    mis = await svc.create_mis(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=await _mis_out(db, mis))


@router.get("/mis/{mis_id}")
async def get_mis(mis_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    mis = await svc.get_mis(mis_id, user.company_id)
    if not mis:
        raise HTTPException(404, "Material issue not found")
    return ApiResponse(success=True, data=await _mis_out(db, mis))


@router.patch("/mis/items/{item_id}/return")
async def record_mis_item_return(item_id: UUID, body: MISItemReturnUpdate, db: DBSession, user: AuthUser):
    """Records Used/Returned/Wastage against an issued material (spec
    §18/§19); a returned quantity flows back into real inventory."""
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        item = await svc.record_mis_item_return(item_id, body, user.company_id, user.user_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not item:
        raise HTTPException(404, "Material issue item not found")
    return ApiResponse(success=True, data=await _mis_item_out(db, item), message="Return recorded")


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
