"""Reports endpoints: sales summary, purchase summary, production efficiency, GST, stock ageing,
and the extended Reports Hub registers (invoice/quotation/order/PO/GRN/ageing/stock/lot-costing/
job-work/material-consumption/receipts/payments/notes/CRM lead ageing)."""
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.models.company import Company
from app.schemas.base import ApiResponse
from app.services.report_export import render_report_table_pdf, report_pdf_filename
from app.services.reports import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


# ── Sales Summary ─────────────────────────────────────────────────────────────

@router.get("/sales-summary")
async def sales_summary(
    db: DBSession, user: AuthUser,
    from_date: date | None = None,
    to_date: date | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    svc = ReportsService(db)
    rows = await svc.sales_summary(user.company_id, fd, td)
    return ApiResponse(success=True, data=rows)


# ── Purchase Summary ──────────────────────────────────────────────────────────

@router.get("/purchase-summary")
async def purchase_summary(
    db: DBSession, user: AuthUser,
    from_date: date | None = None,
    to_date: date | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    svc = ReportsService(db)
    rows = await svc.purchase_summary(user.company_id, fd, td)
    return ApiResponse(success=True, data=rows)


# ── Production Efficiency ─────────────────────────────────────────────────────

@router.get("/production-efficiency")
async def production_efficiency(db: DBSession, user: AuthUser):
    user.require("reports.view")
    svc = ReportsService(db)
    rows = await svc.production_efficiency(user.company_id)
    return ApiResponse(success=True, data=rows)


# ── GST Summary ───────────────────────────────────────────────────────────────

@router.get("/gst-summary")
async def gst_summary(
    db: DBSession, user: AuthUser,
    from_date: date | None = None,
    to_date: date | None = None,
):
    user.require("reports.view")
    today = date.today()
    fd = from_date or today.replace(month=1, day=1)
    td = to_date or today
    svc = ReportsService(db)
    data = await svc.gst_summary(user.company_id, fd, td)
    return ApiResponse(success=True, data=data)


# ── Stock Ageing ──────────────────────────────────────────────────────────────

@router.get("/stock-ageing")
async def stock_ageing(db: DBSession, user: AuthUser, as_of: date | None = None):
    user.require("reports.view")
    svc = ReportsService(db)
    rows = await svc.stock_ageing(user.company_id, as_of=as_of)
    return ApiResponse(success=True, data=rows)


# ── Generic PDF export (any Reports Hub table) ───────────────────────────────
# Renders exactly the rows/columns the browser already fetched and is
# displaying — never a second query — so the PDF can't disagree with the
# on-screen report.

class ReportPdfColumn(BaseModel):
    key: str
    header: str


class ReportPdfTotal(BaseModel):
    label: str
    value: str


class ReportPdfRequest(BaseModel):
    title: str
    subtitle: str | None = None
    columns: list[ReportPdfColumn]
    rows: list[dict[str, Any]]
    totals: list[ReportPdfTotal] = []


@router.post("/export/pdf")
async def export_report_pdf(body: ReportPdfRequest, db: DBSession, user: AuthUser):
    user.require("reports.view")
    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()
    pdf_bytes = render_report_table_pdf(
        company_name=company.name if company else None,
        title=body.title,
        subtitle=body.subtitle,
        columns=[c.model_dump() for c in body.columns],
        rows=body.rows,
        totals=[t.model_dump() for t in body.totals],
    )
    filename = report_pdf_filename(body.title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Invoice Register & AR Ageing ─────────────────────────────────────────────

@router.get("/invoice-register")
async def invoice_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).invoice_register(user.company_id, fd, td, customer_id, status)
    return ApiResponse(success=True, data=rows)


# ── Quotation Register ───────────────────────────────────────────────────────

@router.get("/quotation-register")
async def quotation_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).quotation_register(user.company_id, fd, td, customer_id, status)
    return ApiResponse(success=True, data=rows)


# ── Sales Order Book ─────────────────────────────────────────────────────────

@router.get("/sales-order-book")
async def sales_order_book(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).sales_order_book(user.company_id, fd, td, customer_id, status)
    return ApiResponse(success=True, data=rows)


# ── Sales by Product ─────────────────────────────────────────────────────────

@router.get("/sales-by-product")
async def sales_by_product(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    product_id: UUID | None = None, category_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).sales_by_product(user.company_id, fd, td, product_id, category_id)
    return ApiResponse(success=True, data=rows)


# ── Purchase Order Register ──────────────────────────────────────────────────

@router.get("/po-register")
async def po_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    vendor_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).po_register(user.company_id, fd, td, vendor_id, status)
    return ApiResponse(success=True, data=rows)


# ── GRN Register ──────────────────────────────────────────────────────────────

@router.get("/grn-register")
async def grn_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    vendor_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).grn_register(user.company_id, fd, td, vendor_id, status)
    return ApiResponse(success=True, data=rows)


# ── Vendor Payable Ageing ─────────────────────────────────────────────────────

@router.get("/vendor-payable-ageing")
async def vendor_payable_ageing(
    db: DBSession, user: AuthUser,
    vendor_id: UUID | None = None,
):
    user.require("reports.view")
    rows = await ReportsService(db).vendor_payable_ageing(user.company_id, vendor_id)
    return ApiResponse(success=True, data=rows)


# ── Stock Summary ─────────────────────────────────────────────────────────────

@router.get("/stock-summary")
async def stock_summary(
    db: DBSession, user: AuthUser,
    warehouse_id: UUID | None = None, category_id: UUID | None = None, product_type: str | None = None,
):
    user.require("reports.view")
    rows = await ReportsService(db).stock_summary(user.company_id, warehouse_id, category_id, product_type)
    return ApiResponse(success=True, data=rows)


# ── Material Lot Register ─────────────────────────────────────────────────────

@router.get("/material-lot-register")
async def material_lot_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    material_type: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).material_lot_register(user.company_id, fd, td, material_type)
    return ApiResponse(success=True, data=rows)


# ── Lot Costing Register ──────────────────────────────────────────────────────

@router.get("/lot-costing-register")
async def lot_costing_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, style_id: UUID | None = None, status: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).lot_costing_register(user.company_id, fd, td, customer_id, style_id, status)
    return ApiResponse(success=True, data=rows)


# ── Job-Work Outstanding ──────────────────────────────────────────────────────

@router.get("/job-work-outstanding")
async def job_work_outstanding(
    db: DBSession, user: AuthUser,
    vendor_id: UUID | None = None, worker_id: UUID | None = None, stage_type: str | None = None,
):
    user.require("reports.view")
    rows = await ReportsService(db).job_work_outstanding(user.company_id, vendor_id, worker_id, stage_type)
    return ApiResponse(success=True, data=rows)


# ── Material Consumption ──────────────────────────────────────────────────────

@router.get("/material-consumption")
async def material_consumption(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    lot_id: UUID | None = None, product_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).material_consumption(user.company_id, fd, td, lot_id, product_id)
    return ApiResponse(success=True, data=rows)


# ── Receipt Register (customer payments) ──────────────────────────────────────

@router.get("/receipt-register")
async def receipt_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, payment_mode: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).receipt_register(user.company_id, fd, td, customer_id, payment_mode)
    return ApiResponse(success=True, data=rows)


# ── Payment Register (vendor payments) ────────────────────────────────────────

@router.get("/payment-register")
async def payment_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    vendor_id: UUID | None = None, payment_mode: str | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).payment_register(user.company_id, fd, td, vendor_id, payment_mode)
    return ApiResponse(success=True, data=rows)


# ── Credit Note Register ──────────────────────────────────────────────────────

@router.get("/credit-note-register")
async def credit_note_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).credit_note_register(user.company_id, fd, td, customer_id)
    return ApiResponse(success=True, data=rows)


# ── Debit Note Register ───────────────────────────────────────────────────────

@router.get("/debit-note-register")
async def debit_note_register(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    vendor_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).debit_note_register(user.company_id, fd, td, vendor_id)
    return ApiResponse(success=True, data=rows)


# ── CRM: Lead Conversion & Ageing ─────────────────────────────────────────────

@router.get("/lead-conversion-ageing")
async def lead_conversion_ageing(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    pipeline_id: UUID | None = None, source_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).lead_conversion_ageing(user.company_id, fd, td, pipeline_id, source_id)
    return ApiResponse(success=True, data=rows)


# ── CRM: Employee Task Performance ───────────────────────────────────────────

@router.get("/employee-task-performance")
async def employee_task_performance(db: DBSession, user: AuthUser):
    user.require("reports.view")
    rows = await ReportsService(db).employee_task_performance(user.company_id)
    return ApiResponse(success=True, data=rows)


# ── CRM: Platform-Wise Lead Analytics ────────────────────────────────────────

@router.get("/platform-lead-analytics")
async def platform_lead_analytics(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    source_id: UUID | None = None, assigned_to: UUID | None = None,
    status: str | None = None, customer_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).platform_lead_analytics(
        user.company_id, fd, td, source_id, assigned_to, status, customer_id
    )
    return ApiResponse(success=True, data=rows)


# ── CRM: Lead Acquisition Cost ───────────────────────────────────────────────

@router.get("/lead-acquisition-cost")
async def lead_acquisition_cost(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
    source_id: UUID | None = None,
):
    user.require("reports.view")
    fd, td = from_date or _default_range()[0], to_date or _default_range()[1]
    rows = await ReportsService(db).lead_acquisition_cost(user.company_id, fd, td, source_id)
    return ApiResponse(success=True, data=rows)
