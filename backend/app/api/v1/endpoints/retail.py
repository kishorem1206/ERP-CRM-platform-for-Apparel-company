"""Retail Sales API — counter bills, estimates, retail customers, collections
and discount settings. Separate from the B2B /sales routes."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import Warehouse
from app.models.retail import RetailCoupon, RetailCustomer, RetailEstimate, RetailInvoice
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.retail import (
    RetailCustomerCreate, RetailCustomerOut, RetailCustomerUpdate, RetailEstimateConvert,
    RetailEstimateCreate, RetailEstimateOut, RetailEstimateStatus, RetailInvoiceCancel,
    RetailInvoiceCreate, RetailInvoiceListOut, RetailInvoiceOut, RetailLineOut, RetailPaymentCreate,
    RetailPaymentOut, RetailProductOut, RetailSettingsAuditOut, RetailSettingsOut, RetailSettingsUpdate,
    RetailBillPreview, RetailCouponIn, RetailCouponOut, RetailLoyaltyEntryOut, RetailPointsAdjust,
    RetailCollectIn, RetailPaymentCancel, RetailReturnCreate, RetailReturnItemOut, RetailReturnOut,
)
from app.services.retail_engagement import coupon_state
from app.services.retail import RetailService, outstanding_of

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
        outstanding=outstanding_of(inv),
        due_date=inv.due_date, status=inv.status, estimate_id=inv.estimate_id, cancel_reason=inv.cancel_reason,
        created_at=inv.created_at, discount_approved=inv.discount_approved_by is not None,
        coupon_discount=inv.coupon_discount, points_redeemed=inv.points_redeemed, points_discount=inv.points_discount,
        points_earned=inv.points_earned, points_awarded=inv.points_awarded,
        returned_amount=inv.returned_amount, refunded_amount=inv.refunded_amount, points_returned=inv.points_returned,
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
        outstanding=outstanding_of(inv),
        status=inv.status,
    )


async def _invoice_full(db, inv: RetailInvoice) -> RetailInvoiceOut:
    out = _invoice_out(inv)
    if inv.returned_amount:
        out.returned_qty = {str(k): v for k, v in (await RetailService(db).returned_qty_by_item(inv.id)).items()}
    if inv.coupon_id:
        out.coupon_code = (await db.execute(select(RetailCoupon.code).where(RetailCoupon.id == inv.coupon_id))).scalar_one_or_none()
    return out


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
    out = RetailSettingsOut.model_validate(s, from_attributes=True)
    out.warehouse_name = wh_name
    out.loyalty_excluded_category_ids = list(s.loyalty_excluded_category_ids or [])
    return out


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
    return ApiResponse(success=True, data=await _invoice_full(db, inv), message=f"Bill {inv.invoice_number} saved")


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    inv = await RetailService(db).get_invoice(invoice_id, user.company_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=await _invoice_full(db, inv))


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def record_payment(invoice_id: UUID, body: RetailPaymentCreate, db: DBSession, user: AuthUser):
    user.require("retail.collect")
    inv = await RetailService(db).record_payment(invoice_id, body, user.company_id, user.user_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=await _invoice_full(db, inv), message="Payment recorded")


@router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: UUID, body: RetailInvoiceCancel, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    inv = await RetailService(db).cancel_invoice(invoice_id, body.reason, user.company_id, user.user_id)
    if not inv:
        raise HTTPException(404, "Bill not found")
    return ApiResponse(success=True, data=await _invoice_full(db, inv), message="Bill cancelled — stock returned")


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
    return ApiResponse(success=True, data=await _invoice_full(db, inv), message=f"Billed as {inv.invoice_number}")


# ── Stage 2: bill preview, coupons, loyalty, birthdays ────────────────────────

@router.post("/invoices/preview")
async def preview_invoice(body: RetailInvoiceCreate, db: DBSession, user: AuthUser):
    """What the bill comes to with its coupon and points, without saving."""
    user.require("retail.create")
    svc = RetailService(db)
    customer = await svc.get_customer(body.customer_id, user.company_id) if body.customer_id else None
    on = body.invoice_date or date.today()
    lines, totals = await svc._price(
        body.items, body.bill_discount_pct, user.company_id, user.user_id,
        user.has_permission("retail.discount_approve"),
        customer=customer, coupon_code=body.coupon_code, redeem_points=body.redeem_points, on=on,
    )
    b = totals.pop("_benefits")
    settings = await svc.get_settings(user.company_id)
    max_points = None
    if customer and settings.loyalty_enabled:
        await svc.expire_points(customer, on)
        payable_before_points = totals["total_amount"] + b["points_discount"]
        max_points = min(customer.loyalty_points, int(payable_before_points * settings.max_redeem_pct / 100 / settings.point_value))
    return ApiResponse(success=True, data=RetailBillPreview(
        gross_amount=totals["gross_amount"], discount_amount=totals["discount_amount"],
        coupon_code=b["coupon"].code if b["coupon"] else None, coupon_discount=b["coupon_discount"],
        points_redeemed=b["points_redeemed"], points_discount=b["points_discount"],
        taxable_amount=totals["taxable_amount"], cgst_amount=totals["cgst_amount"], sgst_amount=totals["sgst_amount"],
        round_off=totals["round_off"], total_amount=totals["total_amount"], points_earned=b["points_earned"],
        points_balance=customer.loyalty_points if customer else None, max_redeem_points=max_points,
        lines=[{"net_amount": l["net_amount"], "description": l["description"]} for l in lines],
    ))


def _coupon_out(c, used: int, total, customer_name: str | None = None) -> RetailCouponOut:
    out = RetailCouponOut.model_validate(c, from_attributes=True)
    out.times_used, out.total_discount = used, total
    out.state = coupon_state(c, used, date.today())
    out.customer_name = customer_name
    return out


async def _customer_names(db, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict((await db.execute(select(RetailCustomer.id, RetailCustomer.name).where(RetailCustomer.id.in_(ids)))).all())


@router.get("/coupons")
async def list_coupons(db: DBSession, user: AuthUser, search: str | None = None, kind: str | None = None):
    user.require("retail.view")
    rows = await RetailService(db).list_coupons(user.company_id, search=search, kind=kind)
    names = await _customer_names(db, [c.customer_id for c, _, _ in rows])
    return ApiResponse(success=True, data=[_coupon_out(c, n, t, names.get(c.customer_id)) for c, n, t in rows])


@router.post("/coupons", status_code=201)
async def create_coupon(body: RetailCouponIn, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    c = await RetailService(db).save_coupon(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_coupon_out(c, 0, 0), message=f"Coupon {c.code} created")


@router.put("/coupons/{coupon_id}")
async def update_coupon(coupon_id: UUID, body: RetailCouponIn, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    svc = RetailService(db)
    c = await svc.save_coupon(body, user.company_id, user.user_id, coupon_id=coupon_id)
    used, total = (await svc.coupon_usage([c.id])).get(c.id, (0, 0))
    return ApiResponse(success=True, data=_coupon_out(c, used, total), message="Coupon saved")


@router.get("/coupons/{coupon_id}/redemptions")
async def coupon_redemptions(coupon_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).coupon_redemptions(coupon_id, user.company_id))


@router.get("/customers/{customer_id}/coupons")
async def customer_coupons(customer_id: UUID, db: DBSession, user: AuthUser):
    """Coupons the counter can offer this customer today."""
    user.require("retail.view")
    svc = RetailService(db)
    c = await svc.get_customer(customer_id, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    coupons = await svc.available_coupons(c, user.company_id, date.today())
    return ApiResponse(success=True, data=[_coupon_out(x, 0, 0) for x in coupons])


@router.get("/customers/{customer_id}/points")
async def customer_points(customer_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    svc = RetailService(db)
    c = await svc.get_customer(customer_id, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    await svc.expire_points(c)
    rows = await svc.loyalty_ledger(customer_id, user.company_id)
    return ApiResponse(success=True, data={
        "balance": c.loyalty_points,
        "entries": [RetailLoyaltyEntryOut(
            id=e.id, entry_type=e.entry_type, points=e.points, balance_after=e.balance_after,
            invoice_id=e.invoice_id, invoice_number=num, reason=e.reason, expires_on=e.expires_on, created_at=e.created_at,
        ) for e, num in rows],
    })


@router.post("/customers/{customer_id}/points/adjust")
async def adjust_points(customer_id: UUID, body: RetailPointsAdjust, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    c = await RetailService(db).adjust_points(customer_id, body.points, body.reason, user.company_id, user.user_id)
    return ApiResponse(success=True, data={"balance": c.loyalty_points}, message="Points adjusted")


@router.get("/loyalty/summary")
async def loyalty_summary(db: DBSession, user: AuthUser):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).loyalty_summary(user.company_id))


@router.get("/birthdays")
async def birthdays(db: DBSession, user: AuthUser):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).birthday_dashboard(user.company_id))


@router.post("/birthdays/generate")
async def generate_birthday_coupons(db: DBSession, user: AuthUser):
    user.require("retail.manage")
    made = await RetailService(db).generate_birthday_coupons(user.company_id, user_id=user.user_id)
    return ApiResponse(success=True, data={"created": made},
                       message=f"{made} birthday coupon{'s' if made != 1 else ''} created" if made else "No new birthday coupons due")


# ── Stage 3: credit register, aging, collections, returns ─────────────────────

@router.get("/credit/summary")
async def credit_summary(db: DBSession, user: AuthUser, from_date: date | None = None, to_date: date | None = None):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).credit_summary(user.company_id, date.today(), from_date, to_date))


@router.get("/credit/register")
async def credit_register(
    db: DBSession, user: AuthUser, customer_id: UUID | None = None, search: str | None = None,
    status: str | None = None, min_days_overdue: int | None = None, max_days_overdue: int | None = None,
    from_date: date | None = None, to_date: date | None = None, min_outstanding: Decimal | None = None,
    include_paid: bool = False,
):
    user.require("retail.view")
    rows = await RetailService(db).credit_register(
        user.company_id, date.today(), customer_id=customer_id, search=search, status=status,
        min_days_overdue=min_days_overdue, max_days_overdue=max_days_overdue, from_date=from_date, to_date=to_date,
        min_outstanding=min_outstanding, include_paid=include_paid,
    )
    return ApiResponse(success=True, data=rows)


@router.get("/credit/customers")
async def credit_customers(db: DBSession, user: AuthUser):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).customer_aging(user.company_id, date.today()))


@router.get("/credit/collections")
async def credit_collections(
    db: DBSession, user: AuthUser, from_date: date | None = None, to_date: date | None = None,
    customer_id: UUID | None = None, all_payments: bool = False,
):
    user.require("retail.view")
    return ApiResponse(success=True, data=await RetailService(db).collections(
        user.company_id, from_date, to_date, customer_id, credit_only=not all_payments,
    ))


@router.post("/customers/{customer_id}/collect", status_code=201)
async def collect_from_customer(customer_id: UUID, body: RetailCollectIn, db: DBSession, user: AuthUser):
    user.require("retail.collect")
    svc = RetailService(db)
    batch = await svc.collect_from_customer(
        customer_id, body.amount, body.mode, body.payment_date, body.reference, body.client_ref, user.company_id, user.user_id,
    )
    rows = await svc.receipt(batch, user.company_id)
    return ApiResponse(success=True, data={
        "batch_ref": batch, "receipt_number": rows[0][0].receipt_number if rows else None,
        "allocations": [{"invoice_id": i.id, "invoice_number": i.invoice_number, "amount": p.amount} for p, i in rows],
    }, message="Payment recorded")


@router.post("/payments/{payment_id}/cancel")
async def cancel_payment(payment_id: UUID, body: RetailPaymentCancel, db: DBSession, user: AuthUser):
    user.require("retail.manage")
    pay = await RetailService(db).cancel_payment(payment_id, body.reason, user.company_id, user.user_id)
    return ApiResponse(success=True, data=RetailPaymentOut.model_validate(pay), message="Payment cancelled")


def _return_out(r) -> RetailReturnOut:
    return RetailReturnOut(
        id=r.id, return_number=r.return_number, invoice_id=r.invoice_id,
        invoice_number=r.invoice.invoice_number if r.invoice else None, customer_id=r.customer_id,
        customer_name=r.customer.name if r.customer else None, return_date=r.return_date, reason=r.reason,
        return_amount=r.return_amount, taxable_amount=r.taxable_amount, cgst_amount=r.cgst_amount,
        sgst_amount=r.sgst_amount, applied_to_balance=r.applied_to_balance, refund_amount=r.refund_amount,
        refund_mode=r.refund_mode, points_reversed=r.points_reversed, created_at=r.created_at,
        items=[RetailReturnItemOut.model_validate(i) for i in (r.items if "items" in r.__dict__ else [])],
    )


@router.post("/invoices/{invoice_id}/returns", status_code=201)
async def create_return(invoice_id: UUID, body: RetailReturnCreate, db: DBSession, user: AuthUser):
    user.require("retail.collect")
    r = await RetailService(db).create_return(invoice_id, body, user.company_id, user.user_id)
    msg = f"Return {r.return_number} saved"
    if r.refund_amount:
        msg += f" — refund ₹{r.refund_amount:,.2f}"
    return ApiResponse(success=True, data=_return_out(r), message=msg)


@router.get("/returns")
async def list_returns(db: DBSession, user: AuthUser, invoice_id: UUID | None = None, search: str | None = None):
    user.require("retail.view")
    rows = await RetailService(db).list_returns(user.company_id, invoice_id=invoice_id, search=search)
    return ApiResponse(success=True, data=[_return_out(r) for r in rows])


@router.get("/returns/{return_id}")
async def get_return(return_id: UUID, db: DBSession, user: AuthUser):
    user.require("retail.view")
    r = await RetailService(db).get_return(return_id, user.company_id)
    if not r:
        raise HTTPException(404, "Return not found")
    return ApiResponse(success=True, data=_return_out(r))
