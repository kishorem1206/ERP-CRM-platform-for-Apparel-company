"""Retail Sales API — counter bills, estimates, retail customers, collections
and discount settings. Separate from the B2B /sales routes."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import Warehouse
from app.models.retail import RetailEstimate, RetailInvoice
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.retail import (
    RetailCustomerCreate, RetailCustomerOut, RetailCustomerUpdate, RetailEstimateConvert,
    RetailEstimateCreate, RetailEstimateOut, RetailEstimateStatus, RetailInvoiceCancel,
    RetailInvoiceCreate, RetailInvoiceListOut, RetailInvoiceOut, RetailLineOut, RetailPaymentCreate,
    RetailPaymentOut, RetailProductOut, RetailSettingsAuditOut, RetailSettingsOut, RetailSettingsUpdate,
)
from app.services.retail import RetailService

router = APIRouter(prefix="/retail", tags=["retail"])


def _customer_out(c, stats: dict | None = None) -> RetailCustomerOut:
    out = RetailCustomerOut.model_validate(c, from_attributes=True)
    if stats:
        out.purchase_count = int(stats["purchase_count"] or 0)
        out.total_spent = Decimal(stats["total_spent"] or 0)
        out.products_purchased = Decimal(stats["products_purchased"] or 0)
        out.last_purchase_date = stats["last_purchase_date"]
        out.outstanding = Decimal(stats["outstanding"] or 0)
    return out


def _totals(doc) -> dict:
    return {k: getattr(doc, k) for k in (
        "bill_discount_pct", "gross_amount", "discount_amount", "taxable_amount",
        "cgst_amount", "sgst_amount", "round_off", "total_amount", "notes",
    )}


def _invoice_out(inv: RetailInvoice) -> RetailInvoiceOut:
    return RetailInvoiceOut(
        id=inv.id, invoice_number=inv.invoice_number, customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else None,
        customer_mobile=inv.customer.mobile if inv.customer else None,
        invoice_date=inv.invoice_date, warehouse_id=inv.warehouse_id, payment_mode=inv.payment_mode,
        payment_status=inv.payment_status, amount_paid=inv.amount_paid,
        outstanding=inv.total_amount - inv.amount_paid if inv.status == "active" else Decimal("0"),
        due_date=inv.due_date, status=inv.status, estimate_id=inv.estimate_id, cancel_reason=inv.cancel_reason,
        created_at=inv.created_at, discount_approved=inv.discount_approved_by is not None,
        items=[RetailLineOut.model_validate(i) for i in inv.items],
        payments=[RetailPaymentOut.model_validate(p) for p in inv.payments],
        **_totals(inv),
    )


def _invoice_row(inv: RetailInvoice) -> RetailInvoiceListOut:
    return RetailInvoiceListOut(
        id=inv.id, invoice_number=inv.invoice_number,
        customer_name=inv.customer.name if inv.customer else None,
        customer_mobile=inv.customer.mobile if inv.customer else None,
        invoice_date=inv.invoice_date, payment_mode=inv.payment_mode, payment_status=inv.payment_status,
        total_amount=inv.total_amount, amount_paid=inv.amount_paid,
        outstanding=inv.total_amount - inv.amount_paid if inv.status == "active" else Decimal("0"),
        status=inv.status,
    )


async def _estimate_out(db, est: RetailEstimate, with_items: bool = True) -> RetailEstimateOut:
    converted_number = None
    if est.converted_invoice_id:
        converted_number = (await db.execute(
            select(RetailInvoice.invoice_number).where(RetailInvoice.id == est.converted_invoice_id)
        )).scalar_one_or_none()
    return RetailEstimateOut(
        id=est.id, estimate_number=est.estimate_number, customer_id=est.customer_id,
        customer_name=est.customer.name if est.customer else None,
        customer_mobile=est.customer.mobile if est.customer else None,
        estimate_date=est.estimate_date, valid_until=est.valid_until, status=RetailService.estimate_status(est),
        converted_invoice_id=est.converted_invoice_id, converted_invoice_number=converted_number,
        created_at=est.created_at,
        items=[RetailLineOut.model_validate(i) for i in est.items] if with_items else [],
        **_totals(est),
    )


# ── Settings ──────────────────────────────────────────────────────────────────

async def _settings_out(db, svc: RetailService, company_id) -> RetailSettingsOut:
    s = await svc.get_settings(company_id)
    wh_name = (await db.execute(select(Warehouse.name).where(Warehouse.id == s.warehouse_id))).scalar_one_or_none() if s.warehouse_id else None
    return RetailSettingsOut(
        min_discount_pct=s.min_discount_pct, max_discount_pct=s.max_discount_pct,
        default_discount_pct=s.default_discount_pct, allow_approved_override=s.allow_approved_override,
        warehouse_id=s.warehouse_id, warehouse_name=wh_name, credit_days=s.credit_days,
        estimate_validity_days=s.estimate_validity_days, updated_at=s.updated_at,
    )


@router.get("/settings")
async def get_settings(db: DBSession, user: AuthUser):
    user.require("retail.view")
    return ApiResponse(success=True, data=await _settings_out(db, RetailService(db), user.company_id))


@router.patch("/settings")
async def update_settings(body: RetailSettingsUpdate, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    svc = RetailService(db)
    await svc.update_settings(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=await _settings_out(db, svc, user.company_id), message="Retail settings saved")


@router.get("/settings/audit")
async def settings_audit(db: DBSession, user: AuthUser):
    user.require("retail.manage")
    rows = await RetailService(db).settings_audit(user.company_id)
    names = dict((await db.execute(
        select(User.id, func.coalesce(User.full_name, User.email)).where(User.id.in_({r.changed_by for r in rows if r.changed_by}))
    )).all()) if rows else {}
    return ApiResponse(success=True, data=[RetailSettingsAuditOut(
        field=r.field, old_value=r.old_value, new_value=r.new_value,
        changed_by_name=names.get(r.changed_by), changed_at=r.changed_at,
    ) for r in rows])


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(
    db: DBSession, user: AuthUser, search: str | None = None, city: str | None = None,
    birthday_month: int | None = None, sort: str = "recent", status: str | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("retail.view")
    rows, total = await RetailService(db).list_customers(
        user.company_id, search=search, city=city, birthday_month=birthday_month, sort=sort,
        status=status, page=page, page_size=min(page_size, 200),
    )
    return ApiResponse(success=True, data=[_customer_out(c, s) for c, s in rows],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.get("/customers/by-mobile/{mobile}")
async def customer_by_mobile(mobile: str, db: DBSession, user: AuthUser):
    user.require("retail.view")
    digits = "".join(ch for ch in mobile if ch.isdigit())[-10:]
    svc = RetailService(db)
    c = await svc.find_by_mobile(digits, user.company_id)
    if not c:
        return ApiResponse(success=True, data=None)
    stats = (await svc.customer_stats(user.company_id, [c.id])).get(c.id)
    return ApiResponse(success=True, data=_customer_out(c, stats))


@router.post("/customers", status_code=201)
async def create_customer(body: RetailCustomerCreate, db: DBSession, user: AuthUser):
    user.require("retail.create")
    c = await RetailService(db).create_customer(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_customer_out(c), message="Customer registered")


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    svc = RetailService(db)
    c = await svc.get_customer(customer_id, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    stats = (await svc.customer_stats(user.company_id, [c.id])).get(c.id)
    return ApiResponse(success=True, data=_customer_out(c, stats))


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: UUID, body: RetailCustomerUpdate, db: DBSession, user: AuthUser):
    user.require("retail.create")
    svc = RetailService(db)
    c = await svc.update_customer(customer_id, body, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    stats = (await svc.customer_stats(user.company_id, [c.id])).get(c.id)
    return ApiResponse(success=True, data=_customer_out(c, stats), message="Customer updated")


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/products")
async def search_products(db: DBSession, user: AuthUser, search: str = "", limit: int = 30):
    user.require("retail.view")
    rows = await RetailService(db).search_products(user.company_id, search, min(limit, 100))
    return ApiResponse(success=True, data=[RetailProductOut(**r) for r in rows])


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices")
async def list_invoices(
    db: DBSession, user: AuthUser, search: str | None = None, payment_mode: str | None = None,
    payment_status: str | None = None, customer_id: UUID | None = None,
    from_date: date | None = None, to_date: date | None = None, page: int = 1, page_size: int = 50,
):
    user.require("retail.view")
    rows, total = await RetailService(db).list_invoices(
        user.company_id, search=search, payment_mode=payment_mode, payment_status=payment_status,
        customer_id=customer_id, from_date=from_date, to_date=to_date, page=page, page_size=min(page_size, 200),
    )
    return ApiResponse(success=True, data=[_invoice_row(i) for i in rows],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/invoices", status_code=201)
async def create_invoice(body: RetailInvoiceCreate, db: DBSession, user: AuthUser):
    user.require("retail.create")
    inv = await RetailService(db).create_invoice(
        body, user.company_id, user.user_id, user.has_permission("retail.discount_approve"),
    )
    return ApiResponse(success=True, data=_invoice_out(inv), message=f"Bill {inv.invoice_number} saved")


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    inv = await RetailService(db).get_invoice(invoice_id, user.company_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=_invoice_out(inv))


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def record_payment(invoice_id: UUID, body: RetailPaymentCreate, db: DBSession, user: AuthUser):
    user.require("retail.collect")
    inv = await RetailService(db).record_payment(invoice_id, body, user.company_id, user.user_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=_invoice_out(inv), message="Payment recorded")


@router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: UUID, body: RetailInvoiceCancel, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    inv = await RetailService(db).cancel_invoice(invoice_id, body.reason, user.company_id, user.user_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=_invoice_out(inv), message="Bill cancelled — stock returned")


# ── Estimates ─────────────────────────────────────────────────────────────────

@router.get("/estimates")
async def list_estimates(
    db: DBSession, user: AuthUser, search: str | None = None, status: str | None = None,
    customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
):
    user.require("retail.view")
    rows, total = await RetailService(db).list_estimates(
        user.company_id, search=search, status=status, customer_id=customer_id, page=page, page_size=min(page_size, 200),
    )
    return ApiResponse(success=True, data=[await _estimate_out(db, e, with_items=False) for e in rows],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/estimates", status_code=201)
async def create_estimate(body: RetailEstimateCreate, db: DBSession, user: AuthUser):
    user.require("retail.create")
    est = await RetailService(db).save_estimate(
        body, user.company_id, user.user_id, user.has_permission("retail.discount_approve"),
    )
    return ApiResponse(success=True, data=await _estimate_out(db, est), message=f"Estimate {est.estimate_number} saved")


@router.get("/estimates/{estimate_id}")
async def get_estimate(estimate_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    est = await RetailService(db).get_estimate(estimate_id, user.company_id)
    if not est:
        raise HTTPException(404, "Estimate not found")
    return ApiResponse(success=True, data=await _estimate_out(db, est))


@router.put("/estimates/{estimate_id}")
async def update_estimate(estimate_id: UUID, body: RetailEstimateCreate, db: DBSession, user: AuthUser):
    user.require("retail.create")
    est = await RetailService(db).save_estimate(
        body, user.company_id, user.user_id, user.has_permission("retail.discount_approve"), estimate_id=estimate_id,
    )
    if not est:
        raise HTTPException(404, "Estimate not found")
    return ApiResponse(success=True, data=await _estimate_out(db, est), message="Estimate updated")


@router.post("/estimates/{estimate_id}/status")
async def set_estimate_status(estimate_id: UUID, body: RetailEstimateStatus, db: DBSession, user: AuthUser):
    user.require("retail.create")
    svc = RetailService(db)
    if not await svc.set_estimate_status(estimate_id, body.status, user.company_id):
        raise HTTPException(404, "Estimate not found")
    return ApiResponse(success=True, data=await _estimate_out(db, await svc.get_estimate(estimate_id, user.company_id)))


@router.post("/estimates/{estimate_id}/convert", status_code=201)
async def convert_estimate(estimate_id: UUID, body: RetailEstimateConvert, db: DBSession, user: AuthUser):
    user.require("retail.create")
    inv = await RetailService(db).convert_estimate(
        estimate_id, body, user.company_id, user.user_id, user.has_permission("retail.discount_approve"),
    )
    if not inv:
        raise HTTPException(404, "Estimate not found")
    return ApiResponse(success=True, data=_invoice_out(inv), message=f"Billed as {inv.invoice_number}")
