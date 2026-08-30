"""Reports endpoints: sales summary, purchase summary, production efficiency, GST, stock ageing."""
from datetime import date, timedelta

from fastapi import APIRouter

from app.api.v1.deps import AuthUser, DBSession
from app.schemas.base import ApiResponse
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
async def stock_ageing(db: DBSession, user: AuthUser):
    user.require("reports.view")
    svc = ReportsService(db)
    rows = await svc.stock_ageing(user.company_id)
    return ApiResponse(success=True, data=rows)
