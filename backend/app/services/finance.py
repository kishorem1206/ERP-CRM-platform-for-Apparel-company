"""FinanceService: payments, credit/debit notes, ledger, GST register."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    CreditNote, DebitNote,
    Payment, PaymentAllocation,
    VendorPayment, VendorPaymentAllocation,
)
from app.models.purchase import PurchaseEntry, Vendor
from app.models.sales import Customer, Invoice
from app.schemas.finance import (
    CreditNoteCreate, DebitNoteCreate,
    GSTInputEntry, GSTOutputEntry,
    LedgerEntry,
    PaymentCreate, VendorPaymentCreate,
)

ZERO = Decimal("0")


async def _next_seq(db: AsyncSession, prefix: str, company_id: UUID, model_cls) -> str:
    result = await db.execute(select(func.count()).where(model_cls.company_id == company_id))
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:05d}"


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Payments ───────────────────────────────────────────────────────────────

    async def list_payments(
        self, company_id: UUID, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Payment], int]:
        q = (
            select(Payment)
            .where(Payment.company_id == company_id)
            .options(selectinload(Payment.customer), selectinload(Payment.allocations))
        )
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_payment(self, payment_id: UUID, company_id: UUID) -> Payment | None:
        result = await self.db.execute(
            select(Payment)
            .where(Payment.id == payment_id, Payment.company_id == company_id)
            .options(selectinload(Payment.customer), selectinload(Payment.allocations))
        )
        return result.scalar_one_or_none()

    async def create_payment(self, body: PaymentCreate, company_id: UUID, user_id: UUID) -> Payment:
        now = datetime.now(timezone.utc)
        payment_number = await _next_seq(self.db, "REC", company_id, Payment)

        payment = Payment(
            company_id=company_id, payment_number=payment_number,
            customer_id=body.customer_id, payment_date=body.payment_date,
            amount=body.amount, payment_mode=body.payment_mode,
            reference=body.reference, bank_account=body.bank_account,
            notes=body.notes, created_by=user_id, created_at=now,
        )
        self.db.add(payment)
        await self.db.flush()

        for alloc in body.allocations:
            self.db.add(PaymentAllocation(
                payment_id=payment.id,
                invoice_id=alloc.invoice_id,
                allocated_amount=alloc.allocated_amount,
            ))
            # Update invoice paid_amount / balance / status
            inv_res = await self.db.execute(select(Invoice).where(Invoice.id == alloc.invoice_id))
            inv = inv_res.scalar_one_or_none()
            if inv:
                inv.paid_amount = (inv.paid_amount + alloc.allocated_amount).quantize(Decimal("0.01"))
                inv.balance_amount = (inv.total_amount - inv.paid_amount).quantize(Decimal("0.01"))
                if inv.balance_amount <= ZERO:
                    inv.status = "paid"
                elif inv.paid_amount > ZERO:
                    inv.status = "partial"
                inv.updated_at = now

        await self.db.flush()
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment.id)
            .options(selectinload(Payment.customer), selectinload(Payment.allocations))
        )
        return result.scalar_one()

    # ── Vendor Payments ────────────────────────────────────────────────────────

    async def list_vendor_payments(
        self, company_id: UUID, page: int = 1, page_size: int = 50,
    ) -> tuple[list[VendorPayment], int]:
        q = (
            select(VendorPayment)
            .where(VendorPayment.company_id == company_id)
            .options(selectinload(VendorPayment.vendor), selectinload(VendorPayment.allocations))
        )
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(VendorPayment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_vendor_payment(self, payment_id: UUID, company_id: UUID) -> VendorPayment | None:
        result = await self.db.execute(
            select(VendorPayment)
            .where(VendorPayment.id == payment_id, VendorPayment.company_id == company_id)
            .options(selectinload(VendorPayment.vendor), selectinload(VendorPayment.allocations))
        )
        return result.scalar_one_or_none()

    async def create_vendor_payment(
        self, body: VendorPaymentCreate, company_id: UUID, user_id: UUID,
    ) -> VendorPayment:
        now = datetime.now(timezone.utc)
        payment_number = await _next_seq(self.db, "VPY", company_id, VendorPayment)

        vp = VendorPayment(
            company_id=company_id, payment_number=payment_number,
            vendor_id=body.vendor_id, payment_date=body.payment_date,
            amount=body.amount, payment_mode=body.payment_mode,
            reference=body.reference, bank_account=body.bank_account,
            notes=body.notes, created_by=user_id, created_at=now,
        )
        self.db.add(vp)
        await self.db.flush()

        for alloc in body.allocations:
            self.db.add(VendorPaymentAllocation(
                vendor_payment_id=vp.id,
                purchase_entry_id=alloc.purchase_entry_id,
                allocated_amount=alloc.allocated_amount,
            ))
            # Update purchase entry paid/balance/status
            pe_res = await self.db.execute(
                select(PurchaseEntry).where(PurchaseEntry.id == alloc.purchase_entry_id)
            )
            pe = pe_res.scalar_one_or_none()
            if pe:
                pe.paid_amount = (pe.paid_amount + alloc.allocated_amount).quantize(Decimal("0.01"))
                pe.balance_amount = (pe.total_amount - pe.paid_amount).quantize(Decimal("0.01"))
                if pe.balance_amount <= ZERO:
                    pe.payment_status = "paid"
                elif pe.paid_amount > ZERO:
                    pe.payment_status = "partial"
                pe.updated_at = now

        await self.db.flush()
        result = await self.db.execute(
            select(VendorPayment).where(VendorPayment.id == vp.id)
            .options(selectinload(VendorPayment.vendor), selectinload(VendorPayment.allocations))
        )
        return result.scalar_one()

    # ── Credit Notes ───────────────────────────────────────────────────────────

    async def list_credit_notes(
        self, company_id: UUID, page: int = 1, page_size: int = 50,
    ) -> tuple[list[CreditNote], int]:
        q = (
            select(CreditNote)
            .where(CreditNote.company_id == company_id)
            .options(selectinload(CreditNote.customer))
        )
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(CreditNote.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_credit_note(self, cn_id: UUID, company_id: UUID) -> CreditNote | None:
        result = await self.db.execute(
            select(CreditNote)
            .where(CreditNote.id == cn_id, CreditNote.company_id == company_id)
            .options(selectinload(CreditNote.customer))
        )
        return result.scalar_one_or_none()

    async def create_credit_note(
        self, body: CreditNoteCreate, company_id: UUID, user_id: UUID,
    ) -> CreditNote:
        now = datetime.now(timezone.utc)
        cn_number = await _next_seq(self.db, "CN", company_id, CreditNote)
        cn = CreditNote(
            company_id=company_id, credit_note_number=cn_number,
            customer_id=body.customer_id, invoice_id=body.invoice_id,
            credit_note_date=body.credit_note_date, reason=body.reason,
            taxable_amount=body.taxable_amount, cgst_amount=body.cgst_amount,
            sgst_amount=body.sgst_amount, igst_amount=body.igst_amount,
            total_amount=body.total_amount, notes=body.notes,
            created_by=user_id, created_at=now,
        )
        self.db.add(cn)
        await self.db.flush()
        result = await self.db.execute(
            select(CreditNote).where(CreditNote.id == cn.id)
            .options(selectinload(CreditNote.customer))
        )
        return result.scalar_one()

    # ── Debit Notes ────────────────────────────────────────────────────────────

    async def list_debit_notes(
        self, company_id: UUID, page: int = 1, page_size: int = 50,
    ) -> tuple[list[DebitNote], int]:
        q = (
            select(DebitNote)
            .where(DebitNote.company_id == company_id)
            .options(selectinload(DebitNote.vendor))
        )
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(DebitNote.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_debit_note(self, dn_id: UUID, company_id: UUID) -> DebitNote | None:
        result = await self.db.execute(
            select(DebitNote)
            .where(DebitNote.id == dn_id, DebitNote.company_id == company_id)
            .options(selectinload(DebitNote.vendor))
        )
        return result.scalar_one_or_none()

    async def create_debit_note(
        self, body: DebitNoteCreate, company_id: UUID, user_id: UUID,
    ) -> DebitNote:
        now = datetime.now(timezone.utc)
        dn_number = await _next_seq(self.db, "DN", company_id, DebitNote)
        dn = DebitNote(
            company_id=company_id, debit_note_number=dn_number,
            vendor_id=body.vendor_id, purchase_entry_id=body.purchase_entry_id,
            debit_note_date=body.debit_note_date, reason=body.reason,
            total_amount=body.total_amount, notes=body.notes,
            created_by=user_id, created_at=now,
        )
        self.db.add(dn)
        await self.db.flush()
        result = await self.db.execute(
            select(DebitNote).where(DebitNote.id == dn.id)
            .options(selectinload(DebitNote.vendor))
        )
        return result.scalar_one()

    # ── Customer Ledger ────────────────────────────────────────────────────────

    async def get_customer_ledger(
        self, customer_id: UUID, company_id: UUID,
        from_date=None, to_date=None,
    ) -> list[LedgerEntry]:
        entries: list[tuple] = []

        # Invoices (debit — money owed to us)
        inv_q = select(Invoice).where(
            Invoice.customer_id == customer_id,
            Invoice.company_id == company_id,
        )
        if from_date:
            inv_q = inv_q.where(Invoice.invoice_date >= from_date)
        if to_date:
            inv_q = inv_q.where(Invoice.invoice_date <= to_date)
        for inv in (await self.db.execute(inv_q)).scalars().all():
            entries.append((inv.invoice_date, "Invoice", inv.invoice_number,
                            "Sales Invoice", inv.total_amount, ZERO))

        # Payments (credit — money received)
        pay_q = select(Payment).where(
            Payment.customer_id == customer_id,
            Payment.company_id == company_id,
        )
        if from_date:
            pay_q = pay_q.where(Payment.payment_date >= from_date)
        if to_date:
            pay_q = pay_q.where(Payment.payment_date <= to_date)
        for pay in (await self.db.execute(pay_q)).scalars().all():
            entries.append((pay.payment_date, "Payment", pay.payment_number,
                            f"Receipt ({pay.payment_mode})", ZERO, pay.amount))

        # Credit Notes (credit)
        cn_q = select(CreditNote).where(
            CreditNote.customer_id == customer_id,
            CreditNote.company_id == company_id,
        )
        if from_date:
            cn_q = cn_q.where(CreditNote.credit_note_date >= from_date)
        if to_date:
            cn_q = cn_q.where(CreditNote.credit_note_date <= to_date)
        for cn in (await self.db.execute(cn_q)).scalars().all():
            entries.append((cn.credit_note_date, "CreditNote", cn.credit_note_number,
                            "Credit Note", ZERO, cn.total_amount))

        entries.sort(key=lambda x: x[0])

        balance = ZERO
        ledger: list[LedgerEntry] = []
        for entry_date, doc_type, doc_number, description, debit, credit in entries:
            balance = balance + debit - credit
            ledger.append(LedgerEntry(
                entry_date=entry_date, doc_type=doc_type, doc_number=doc_number,
                description=description, debit=debit, credit=credit, balance=balance,
            ))
        return ledger

    # ── Vendor Ledger ──────────────────────────────────────────────────────────

    async def get_vendor_ledger(
        self, vendor_id: UUID, company_id: UUID,
        from_date=None, to_date=None,
    ) -> list[LedgerEntry]:
        entries: list[tuple] = []

        # Purchase entries (credit — money we owe vendor)
        pe_q = select(PurchaseEntry).where(
            PurchaseEntry.vendor_id == vendor_id,
            PurchaseEntry.company_id == company_id,
        )
        if from_date:
            pe_q = pe_q.where(PurchaseEntry.entry_date >= from_date)
        if to_date:
            pe_q = pe_q.where(PurchaseEntry.entry_date <= to_date)
        for pe in (await self.db.execute(pe_q)).scalars().all():
            entries.append((pe.entry_date, "Purchase", pe.entry_number,
                            "Purchase Entry", ZERO, pe.total_amount))

        # Vendor Payments (debit — money we paid)
        vp_q = select(VendorPayment).where(
            VendorPayment.vendor_id == vendor_id,
            VendorPayment.company_id == company_id,
        )
        if from_date:
            vp_q = vp_q.where(VendorPayment.payment_date >= from_date)
        if to_date:
            vp_q = vp_q.where(VendorPayment.payment_date <= to_date)
        for vp in (await self.db.execute(vp_q)).scalars().all():
            entries.append((vp.payment_date, "VendorPayment", vp.payment_number,
                            f"Payment ({vp.payment_mode})", vp.amount, ZERO))

        # Debit Notes (debit — reduces what we owe)
        dn_q = select(DebitNote).where(
            DebitNote.vendor_id == vendor_id,
            DebitNote.company_id == company_id,
        )
        if from_date:
            dn_q = dn_q.where(DebitNote.debit_note_date >= from_date)
        if to_date:
            dn_q = dn_q.where(DebitNote.debit_note_date <= to_date)
        for dn in (await self.db.execute(dn_q)).scalars().all():
            entries.append((dn.debit_note_date, "DebitNote", dn.debit_note_number,
                            "Debit Note", dn.total_amount, ZERO))

        entries.sort(key=lambda x: x[0])

        balance = ZERO
        ledger: list[LedgerEntry] = []
        for entry_date, doc_type, doc_number, description, debit, credit in entries:
            balance = balance + credit - debit
            ledger.append(LedgerEntry(
                entry_date=entry_date, doc_type=doc_type, doc_number=doc_number,
                description=description, debit=debit, credit=credit, balance=balance,
            ))
        return ledger

    # ── GST Output Register (GSTR-1) ───────────────────────────────────────────

    async def get_gst_output(
        self, company_id: UUID, from_date=None, to_date=None,
    ) -> list[GSTOutputEntry]:
        q = (
            select(Invoice)
            .where(Invoice.company_id == company_id)
            .options(selectinload(Invoice.customer))
        )
        if from_date:
            q = q.where(Invoice.invoice_date >= from_date)
        if to_date:
            q = q.where(Invoice.invoice_date <= to_date)
        invoices = (await self.db.execute(q)).scalars().all()
        return [
            GSTOutputEntry(
                invoice_date=inv.invoice_date,
                invoice_number=inv.invoice_number,
                customer_name=inv.customer.legal_name if inv.customer else "",
                gstin=inv.customer.gstin if inv.customer else None,
                taxable_amount=inv.taxable_amount,
                cgst_amount=inv.cgst_amount,
                sgst_amount=inv.sgst_amount,
                igst_amount=inv.igst_amount,
                total_amount=inv.total_amount,
            )
            for inv in invoices
        ]

    # ── GST Input Register (GSTR-2A) ───────────────────────────────────────────

    async def get_gst_input(
        self, company_id: UUID, from_date=None, to_date=None,
    ) -> list[GSTInputEntry]:
        q = (
            select(PurchaseEntry)
            .where(PurchaseEntry.company_id == company_id)
            .options(selectinload(PurchaseEntry.vendor))
        )
        if from_date:
            q = q.where(PurchaseEntry.entry_date >= from_date)
        if to_date:
            q = q.where(PurchaseEntry.entry_date <= to_date)
        entries = (await self.db.execute(q)).scalars().all()
        return [
            GSTInputEntry(
                entry_date=pe.entry_date,
                entry_number=pe.entry_number,
                vendor_name=pe.vendor.name if pe.vendor else "",
                gstin=pe.vendor.gstin if pe.vendor else None,
                invoice_number=pe.invoice_number,
                taxable_amount=pe.taxable_amount,
                cgst_amount=pe.cgst_amount,
                sgst_amount=pe.sgst_amount,
                igst_amount=pe.igst_amount,
                total_amount=pe.total_amount,
            )
            for pe in entries
        ]
