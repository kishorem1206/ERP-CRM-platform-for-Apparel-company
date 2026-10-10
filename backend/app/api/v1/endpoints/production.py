"""Production module endpoints: styles, lots, stages, MIS, outputs."""
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import AuthUser, DBSession
from app.models.company import Company
from app.models.inventory import InventoryLot
from app.models.master import Product, Unit, Warehouse
from app.models.production import InternalWorker, MaterialIssue, ProductionLot, ProductionOutput, ProductionStage, ProductionStageChallan
from app.models.purchase import Vendor
from app.models.sales import Customer
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.production import (
    FabricProcessingComplete, FabricProcessingCreate, FabricProcessingOut, FabricProcessingUpdate,
    InternalWorkerCreate, InternalWorkerOut,
    LotAdditionalCostCreate, LotAdditionalCostOut, LotAdditionalCostUpdate,
    LotFabricActualUpdate, LotFabricOut, LotYarnActualUpdate, LotYarnOut,
    ProductionAuditLogOut, ProductionDashboardOut, ProductionDashboardRow, ProductionDashboardTotals,
    LotPackingActualUpdate, LotPackingMaterialOut, LotTrimActualUpdate, LotTrimOut,
    MaterialIssueCreate, MaterialIssueOut, MISItemOut, MISItemReturnUpdate,
    MistakeLogCreate, MistakeLogOut,
    LotBomOut, LotPartColourOut, LotProductionSummaryOut,
    ProductionLotCreate, ProductionLotOut, ProductionLotUpdate,
    ProductionOutputCreate, ProductionOutputOut,
    SizeChartCreate, SizeChartOut,
    StageChallanBillUpdate, StageChallanCreate, StageChallanOut, StageChallanReceive,
    StageCreate, StageEntryCreate, StageEntryOut, StageOperationOut, StageOut, StageSizeOut, StageSizeUpdate, StageUpdate,
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
    for sz_out in out.sizes:
        sz_out.pending_qty = max(sz_out.input_qty - sz_out.accepted_qty - sz_out.rejected_qty - sz_out.rework_qty, 0)

    # Operation cost attribution (Phase 7 — Wages): apportion this stage's
    # own actual cost across its configured Operations by relative
    # planned_rate weight — a computed view of the one existing total,
    # never a second stored amount, so it can't double-count against it.
    sub_processes = s.style_process.sub_processes if s.style_process else []
    actual_total = s.bill_amount if s.bill_amount is not None else (
        s.rate_per_pc * out.accepted_qty if s.rate_per_pc is not None and out.accepted_qty else None
    )
    if sub_processes and actual_total is not None:
        rated = [sp for sp in sub_processes if sp.planned_rate]
        weight_total = sum(sp.planned_rate for sp in rated) if rated else None
        out.operations = [
            StageOperationOut(
                name=sp.name, planned_rate=sp.planned_rate,
                estimated_cost_share=(actual_total * sp.planned_rate / weight_total) if (weight_total and sp.planned_rate) else None,
            )
            for sp in sorted(sub_processes, key=lambda sp: sp.seq)
        ]
    elif sub_processes:
        out.operations = [StageOperationOut(name=sp.name, planned_rate=sp.planned_rate, estimated_cost_share=None) for sp in sorted(sub_processes, key=lambda sp: sp.seq)]

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

    out.completion_warnings = _stage_completion_warnings(s, out)
    return out


def _stage_completion_warnings(s: ProductionStage, out: StageOut) -> list[str]:
    """What still looks unrecorded before this stage is marked complete.
    Advisory only — the user can complete anyway after seeing the list."""
    warnings: list[str] = []
    if s.assignment_type:
        if s.sent_qty == 0:
            warnings.append("Nothing has been sent out to the vendor/worker yet.")
        else:
            with_vendor = s.sent_qty - s.received_qty - s.rejected_qty
            if with_vendor > 0:
                warnings.append(f"{with_vendor} pcs are still out with the vendor/worker — challan not fully received.")
    elif s.input_qty == 0 and s.output_qty == 0:
        warnings.append("No production entries logged — input and output are both 0.")
    elif s.output_qty == 0:
        warnings.append("Input is logged but no output has been recorded.")

    accounted = out.accepted_qty + s.rejected_qty
    if s.planned_qty and 0 < accounted < s.planned_qty:
        warnings.append(f"{s.planned_qty - accounted} of {s.planned_qty} planned pcs are not yet accounted for (accepted + rejected).")

    sized = [sz for sz in s.sizes if sz.input_qty > 0]
    unfilled = [sz for sz in sized if sz.accepted_qty + sz.rejected_qty + sz.rework_qty < sz.input_qty]
    if unfilled:
        pending = sum(sz.input_qty - sz.accepted_qty - sz.rejected_qty - sz.rework_qty for sz in unfilled)
        warnings.append(f"Size-wise accept/reject is incomplete for {len(unfilled)} of {len(sized)} sizes ({pending} pcs pending).")

    if (s.input_unit or "").lower() == "kg" and s.input_weight_kg is None:
        warnings.append("This is a weight-based stage but no input weight has been recorded.")

    if s.rate_per_pc is None and s.bill_amount is None:
        warnings.append("No rate per piece or bill amount — this stage's cost won't be included in lot costing.")
    return warnings


def _packing_materials_out(rows) -> list[LotPackingMaterialOut]:
    out = []
    for p in rows:
        o = LotPackingMaterialOut.model_validate(p)
        o.product_name = p.product.name if p.product else None
        out.append(o)
    return out


def _lot_part_colours_out(rows) -> list[LotPartColourOut]:
    out = []
    for pc in rows:
        o = LotPartColourOut.model_validate(pc)
        o.style_part_name = pc.style_part.name if pc.style_part else None
        o.colour_name = pc.colour.name if pc.colour else None
        out.append(o)
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
        part_colours=_lot_part_colours_out(lot.part_colours),
        stages=[_stage_out(s) for s in sorted(lot.stages, key=lambda s: s.created_at)],
        additional_costs=[LotAdditionalCostOut.model_validate(a) for a in lot.additional_costs],
        trims=[LotTrimOut.model_validate(t) for t in lot.trims],
        packing_materials=_packing_materials_out(lot.packing_materials),
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
    out.brand_name = s.brand.name if s.brand else None
    for pc, pc_out in zip(s.part_colours, out.part_colours):
        pc_out.style_part_name = pc.style_part.name if pc.style_part else None
    for fb, fb_out in zip(s.fabrics, out.fabrics):
        fb_out.style_part_name = fb.style_part.name if fb.style_part else None
    for yn, yn_out in zip(s.yarns, out.yarns):
        yn_out.fabric_name = yn.style_fabric.fabric_name if yn.style_fabric else None
        yn_out.colour_name = yn.colour.name if yn.colour else None
    for tr, tr_out in zip(s.trims, out.trims):
        tr_out.style_part_name = tr.style_part.name if tr.style_part else None
        tr_out.colour_name = tr.colour.name if tr.colour else None
    for pr, pr_out in zip(s.processes, out.processes):
        pr_out.style_part_name = pr.style_part.name if pr.style_part else None
    out.total_tolerance_pct = sum(
        (p.tolerance_pct for p in s.processes if p.is_enabled and p.tolerance_pct is not None),
        Decimal("0"),
    )
    return out


async def _mis_item_out(db: DBSession, item) -> MISItemOut:
    out = MISItemOut.model_validate(item)
    if item.planned_qty is not None and item.issued_qty > item.planned_qty:
        out.excess_qty = item.issued_qty - item.planned_qty   # §47.4 — excess must stay visible
    out.product_name = (await db.execute(select(Product.name).where(Product.id == item.product_id))).scalar_one_or_none()
    out.unit_abbreviation = (await db.execute(select(Unit.abbreviation).where(Unit.id == item.unit_id))).scalar_one_or_none()
    out.material_lot_id = item.lot_id
    if item.lot_id:
        out.material_lot_number = (await db.execute(select(InventoryLot.lot_number).where(InventoryLot.id == item.lot_id))).scalar_one_or_none()
    return out


async def _mis_out(db: DBSession, mis: MaterialIssue) -> MaterialIssueOut:
    warehouse_name = (await db.execute(select(Warehouse.name).where(Warehouse.id == mis.warehouse_id))).scalar_one_or_none()
    stage_name = None
    if mis.stage_id:
        stage_name = (await db.execute(select(ProductionStage.stage_name).where(ProductionStage.id == mis.stage_id))).scalar_one_or_none()
    return MaterialIssueOut(
        id=mis.id, issue_number=mis.issue_number,
        production_lot_id=mis.production_lot_id,
        lot_number=mis.production_lot.lot_number if mis.production_lot else None,
        stage_id=mis.stage_id, stage_name=stage_name,
        warehouse_id=mis.warehouse_id, warehouse_name=warehouse_name,
        issue_date=mis.issue_date, status=mis.status, notes=mis.notes,
        items=[await _mis_item_out(db, i) for i in mis.items],
    )


async def _output_out(db: DBSession, o: ProductionOutput) -> ProductionOutputOut:
    warehouse_name = (await db.execute(select(Warehouse.name).where(Warehouse.id == o.warehouse_id))).scalar_one_or_none()
    product_name = (await db.execute(select(Product.name).where(Product.id == o.product_id))).scalar_one_or_none()
    unit_abbreviation = (await db.execute(select(Unit.abbreviation).where(Unit.id == o.unit_id))).scalar_one_or_none()
    return ProductionOutputOut(
        id=o.id, output_number=o.output_number,
        production_lot_id=o.production_lot_id,
        lot_number=o.production_lot.lot_number if o.production_lot else None,
        warehouse_id=o.warehouse_id, warehouse_name=warehouse_name, output_date=o.output_date,
        product_id=o.product_id, product_name=product_name,
        variant_id=o.variant_id, quantity=o.quantity, rejected_qty=o.rejected_qty,
        unit_id=o.unit_id, unit_abbreviation=unit_abbreviation, unit_cost=o.unit_cost, total_cost=o.total_cost,
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


# ── Production Progress Dashboard (Phase 11) ──────────────────────────────────

@router.get("/dashboard")
async def production_dashboard(db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    dashboard = await svc.build_production_dashboard(user.company_id)
    customer_ids = {r["customer_id"] for r in dashboard["rows"] if r["customer_id"]}
    customer_names: dict = {}
    if customer_ids:
        rows = (await db.execute(select(Customer.id, Customer.legal_name).where(Customer.id.in_(customer_ids)))).all()
        customer_names = {cid: name for cid, name in rows}
    for r in dashboard["rows"]:
        r["customer_name"] = customer_names.get(r["customer_id"])
    out = ProductionDashboardOut(
        rows=[ProductionDashboardRow(**r) for r in dashboard["rows"]],
        totals=ProductionDashboardTotals(**dashboard["totals"]),
        lots_by_status=dashboard["lots_by_status"],
    )
    return ApiResponse(success=True, data=out)


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


@router.get("/lots/{lot_id}/bom")
async def get_lot_bom(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    lot = await svc.get_lot(lot_id, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    bom = await svc.build_lot_bom(lot)
    return ApiResponse(success=True, data=LotBomOut(**bom))


class StatusBody(ProductionLotUpdate):
    status: str


@router.post("/lots/{lot_id}/status")
async def advance_lot_status(lot_id: UUID, body: StatusBody, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    lot = await svc.advance_lot_status(lot_id, user.company_id, body.status, user.user_id)
    if not lot:
        raise HTTPException(400, "Lot not found or invalid status transition")
    return ApiResponse(success=True, data=await _lot_out(lot, svc))


@router.post("/lots/{lot_id}/reopen")
async def reopen_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        lot = await svc.reopen_lot(lot_id, user.company_id, user.user_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not lot:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=await _lot_out(lot, svc), message="Lot reopened")


@router.get("/lots/{lot_id}/audit-log")
async def get_lot_audit_log(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    rows = await svc.list_audit_log(lot_id, user.company_id)
    user_ids = {r.changed_by for r in rows if r.changed_by}
    names: dict = {}
    if user_ids:
        names = {uid: n for uid, n in (await db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))).all()}
    data = []
    for r in rows:
        out = ProductionAuditLogOut.model_validate(r)
        out.changed_by_name = names.get(r.changed_by)
        data.append(out)
    return ApiResponse(success=True, data=data)


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
        stage = await svc.update_stage(stage_id, body, user.company_id, user.user_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not stage:
        raise HTTPException(404, "Stage not found")
    return ApiResponse(success=True, data=_stage_out(stage), message="Stage updated")


@router.patch("/stages/{stage_id}/sizes/{size_id}")
async def update_stage_size(stage_id: UUID, size_id: UUID, body: StageSizeUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    try:
        row = await svc.update_stage_size(stage_id, size_id, body, user.company_id)
    except QuantityValidationError as exc:
        raise HTTPException(422, str(exc))
    if not row:
        raise HTTPException(404, "Stage/size not found")
    out = StageSizeOut.model_validate(row)
    out.pending_qty = max(out.input_qty - out.accepted_qty - out.rejected_qty - out.rework_qty, 0)
    return ApiResponse(success=True, data=out, message="Updated")


@router.get("/lots/{lot_id}/summary")
async def get_lot_production_summary(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    lot = await svc.get_lot(lot_id, user.company_id)
    if not lot:
        raise HTTPException(404, "Production lot not found")
    summary = svc.build_lot_production_summary(lot)
    return ApiResponse(success=True, data=LotProductionSummaryOut(**summary))


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


@router.patch("/lots/fabrics/{fabric_id}")
async def update_lot_fabric(fabric_id: UUID, body: LotFabricActualUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    fabric = await svc.update_lot_fabric_actual(fabric_id, body, user.company_id)
    if not fabric:
        raise HTTPException(404, "Lot fabric not found")
    return ApiResponse(success=True, data=LotFabricOut.model_validate(fabric), message="Fabric actual quantity updated")


@router.patch("/lots/yarns/{yarn_id}")
async def update_lot_yarn(yarn_id: UUID, body: LotYarnActualUpdate, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    yarn = await svc.update_lot_yarn_actual(yarn_id, body, user.company_id)
    if not yarn:
        raise HTTPException(404, "Lot yarn not found")
    return ApiResponse(success=True, data=LotYarnOut.model_validate(yarn), message="Yarn actual quantity updated")


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
    return ApiResponse(success=True, data=[await _output_out(db, o) for o in outputs],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/outputs", status_code=201)
async def create_output(body: ProductionOutputCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    output = await svc.create_output(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=await _output_out(db, output))


@router.get("/outputs/{output_id}")
async def get_output(output_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    output = await svc.get_output(output_id, user.company_id)
    if not output:
        raise HTTPException(404, "Production output not found")
    return ApiResponse(success=True, data=await _output_out(db, output))


# ── Mistake Log (16-item request #15) ────────────────────────────────────────

def _mistake_log_out(log) -> MistakeLogOut:
    out = MistakeLogOut.model_validate(log)
    out.stage_name = log.stage.stage_name if log.stage else None
    out.resolved_staff_name = (log.staff.name if log.staff else None) or log.staff_name
    return out


@router.get("/lots/{lot_id}/mistake-logs")
async def list_mistake_logs(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.view")
    svc = ProductionService(db)
    logs = await svc.list_mistake_logs(lot_id, user.company_id)
    return ApiResponse(success=True, data=[_mistake_log_out(l) for l in logs])


@router.post("/lots/{lot_id}/mistake-logs", status_code=201)
async def create_mistake_log(lot_id: UUID, body: MistakeLogCreate, db: DBSession, user: AuthUser):
    user.require("production.create")
    svc = ProductionService(db)
    log = await svc.create_mistake_log(lot_id, body, user.company_id, user.user_id)
    if not log:
        raise HTTPException(404, "Production lot not found")
    return ApiResponse(success=True, data=_mistake_log_out(log))


@router.delete("/lots/mistake-logs/{log_id}")
async def delete_mistake_log(log_id: UUID, db: DBSession, user: AuthUser):
    user.require("production.edit")
    svc = ProductionService(db)
    ok = await svc.delete_mistake_log(log_id, user.company_id)
    if not ok:
        raise HTTPException(404, "Mistake log not found")
    return ApiResponse(success=True, data=None, message="Mistake log deleted")
