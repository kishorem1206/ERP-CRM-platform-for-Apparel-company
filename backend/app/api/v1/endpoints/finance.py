"""Finance module endpoints: payments, credit/debit notes, ledger, GST register."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.v1.deps import AuthUser, DBSession
from app.models.finance import CreditNote, DebitNote, Payment, VendorPayment
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.finance import (
    CreditNoteCreate, CreditNoteOut,
    DebitNoteCreate, DebitNoteOut,
    PaymentCreate, PaymentOut, PaymentAllocationOut,
    VendorPaymentCreate, VendorPaymentOut, VendorPaymentAllocationOut,
)
from app.services.finance import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


def _pay_out(pay: Payment) -> PaymentOut:
    return PaymentOut(
        id=pay.id, payment_number=pay.payment_number,
        customer_id=pay.customer_id,
        customer_name=pay.customer.legal_name if pay.customer else None,
        payment_date=pay.payment_date, amount=pay.amount,
        payment_mode=pay.payment_mode, reference=pay.reference,
        bank_account=pay.bank_account, notes=pay.notes, status=pay.status,
        allocations=[PaymentAllocationOut.model_validate(a) for a in pay.allocations],
    )


def _vpay_out(vp: VendorPayment) -> VendorPaymentOut:
    return VendorPaymentOut(
        id=vp.id, payment_number=vp.payment_number,
        vendor_id=vp.vendor_id,
        vendor_name=vp.vendor.name if vp.vendor else None,
        payment_date=vp.payment_date, amount=vp.amount,
        payment_mode=vp.payment_mode, reference=vp.reference,
        bank_account=vp.bank_account, notes=vp.notes, status=vp.status,
        allocations=[VendorPaymentAllocationOut.model_validate(a) for a in vp.allocations],
    )


def _cn_out(cn: CreditNote) -> CreditNoteOut:
    return CreditNoteOut(
        id=cn.id, credit_note_number=cn.credit_note_number,
        customer_id=cn.customer_id,
        customer_name=cn.customer.legal_name if cn.customer else None,
        invoice_id=cn.invoice_id, credit_note_date=cn.credit_note_date,
        reason=cn.reason, taxable_amount=cn.taxable_amount,
        cgst_amount=cn.cgst_amount, sgst_amount=cn.sgst_amount,
        igst_amount=cn.igst_amount, total_amount=cn.total_amount,
        status=cn.status, notes=cn.notes,
    )


def _dn_out(dn: DebitNote) -> DebitNoteOut:
    return DebitNoteOut(
        id=dn.id, debit_note_number=dn.debit_note_number,
        vendor_id=dn.vendor_id,
        vendor_name=dn.vendor.name if dn.vendor else None,
        purchase_entry_id=dn.purchase_entry_id, debit_note_date=dn.debit_note_date,
        reason=dn.reason, total_amount=dn.total_amount,
        status=dn.status, notes=dn.notes,
    )


# ── Customer Payments ──────────────────────────────────────────────────────────

@router.get("/payments")
async def list_payments(db: DBSession, user: AuthUser, page: int = 1, page_size: int = 50):
    user.require("finance.view")
    svc = FinanceService(db)
    pays, total = await svc.list_payments(user.company_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_pay_out(p) for p in pays],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/payments", status_code=201)
async def create_payment(body: PaymentCreate, db: DBSession, user: AuthUser):
    user.require("finance.create")
    svc = FinanceService(db)
    pay = await svc.create_payment(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_pay_out(pay))


@router.get("/payments/{payment_id}")
async def get_payment(payment_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    svc = FinanceService(db)
    pay = await svc.get_payment(payment_id, user.company_id)
    if not pay:
        raise HTTPException(404, "Payment not found")
    return ApiResponse(success=True, data=_pay_out(pay))


# ── Vendor Payments ────────────────────────────────────────────────────────────

@router.get("/vendor-payments")
async def list_vendor_payments(db: DBSession, user: AuthUser, page: int = 1, page_size: int = 50):
    user.require("finance.view")
    svc = FinanceService(db)
    pays, total = await svc.list_vendor_payments(user.company_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_vpay_out(p) for p in pays],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/vendor-payments", status_code=201)
async def create_vendor_payment(body: VendorPaymentCreate, db: DBSession, user: AuthUser):
    user.require("finance.create")
    svc = FinanceService(db)
    vp = await svc.create_vendor_payment(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_vpay_out(vp))


@router.get("/vendor-payments/{payment_id}")
async def get_vendor_payment(payment_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    svc = FinanceService(db)
    vp = await svc.get_vendor_payment(payment_id, user.company_id)
    if not vp:
        raise HTTPException(404, "Vendor payment not found")
    return ApiResponse(success=True, data=_vpay_out(vp))


# ── Credit Notes ───────────────────────────────────────────────────────────────

@router.get("/credit-notes")
async def list_credit_notes(db: DBSession, user: AuthUser, page: int = 1, page_size: int = 50):
    user.require("finance.view")
    svc = FinanceService(db)
    cns, total = await svc.list_credit_notes(user.company_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_cn_out(c) for c in cns],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/credit-notes", status_code=201)
async def create_credit_note(body: CreditNoteCreate, db: DBSession, user: AuthUser):
    user.require("finance.create")
    svc = FinanceService(db)
    cn = await svc.create_credit_note(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_cn_out(cn))


@router.get("/credit-notes/{cn_id}")
async def get_credit_note(cn_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    svc = FinanceService(db)
    cn = await svc.get_credit_note(cn_id, user.company_id)
    if not cn:
        raise HTTPException(404, "Credit note not found")
    return ApiResponse(success=True, data=_cn_out(cn))


# ── Debit Notes ────────────────────────────────────────────────────────────────

@router.get("/debit-notes")
async def list_debit_notes(db: DBSession, user: AuthUser, page: int = 1, page_size: int = 50):
    user.require("finance.view")
    svc = FinanceService(db)
    dns, total = await svc.list_debit_notes(user.company_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_dn_out(d) for d in dns],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/debit-notes", status_code=201)
async def create_debit_note(body: DebitNoteCreate, db: DBSession, user: AuthUser):
    user.require("finance.create")
    svc = FinanceService(db)
    dn = await svc.create_debit_note(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_dn_out(dn))


@router.get("/debit-notes/{dn_id}")
async def get_debit_note(dn_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    svc = FinanceService(db)
    dn = await svc.get_debit_note(dn_id, user.company_id)
    if not dn:
        raise HTTPException(404, "Debit note not found")
    return ApiResponse(success=True, data=_dn_out(dn))


# ── Ledger ─────────────────────────────────────────────────────────────────────

@router.get("/ledger/customer/{customer_id}")
async def get_customer_ledger(
    customer_id: UUID, db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
):
    user.require("finance.view")
    svc = FinanceService(db)
    entries = await svc.get_customer_ledger(customer_id, user.company_id, from_date, to_date)
    return ApiResponse(success=True, data=entries)


@router.get("/ledger/vendor/{vendor_id}")
async def get_vendor_ledger(
    vendor_id: UUID, db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
):
    user.require("finance.view")
    svc = FinanceService(db)
    entries = await svc.get_vendor_ledger(vendor_id, user.company_id, from_date, to_date)
    return ApiResponse(success=True, data=entries)


# ── GST Register ───────────────────────────────────────────────────────────────

@router.get("/gst/output")
async def gst_output(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
):
    user.require("finance.view")
    svc = FinanceService(db)
    entries = await svc.get_gst_output(user.company_id, from_date, to_date)
    return ApiResponse(success=True, data=entries)


@router.get("/gst/input")
async def gst_input(
    db: DBSession, user: AuthUser,
    from_date: date | None = None, to_date: date | None = None,
):
    user.require("finance.view")
    svc = FinanceService(db)
    entries = await svc.get_gst_input(user.company_id, from_date, to_date)
    return ApiResponse(success=True, data=entries)
