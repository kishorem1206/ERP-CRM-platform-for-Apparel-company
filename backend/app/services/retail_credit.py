"""Retail Sales stage 3 — credit collections, aging, receipts and returns.

Mixed into RetailService (uses self.db, self.inv, self.get_settings,
self._next_number, self._add_points, self.get_invoice ...).

Money rules:
- A bill's outstanding = total - returned - (paid - refunded).
- A credit bill's value is a sale on its date; collections against it are
  collections, never sales again.
- Aging is measured from the due date: not yet due, 1-30, 31-60, 61-90 and
  over 90 days overdue.
- A return first reduces what is still owed on that bill; anything beyond
  that is refunded. Points earned on the bill shrink in proportion.
"""
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select

from app.domain.business_rules import BusinessRulesError
from app.models.retail import (
    RetailCustomer, RetailInvoice, RetailInvoiceItem, RetailPayment, RetailReturn, RetailReturnItem,
)
from app.schemas.inventory import ReceiveParams

CENT = Decimal("0.01")
ZERO = Decimal("0")
BUCKETS = ("not_due", "d1_30", "d31_60", "d61_90", "d90_plus")


def _q(v) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


def _outstanding(inv: RetailInvoice) -> Decimal:
    if inv.status != "active":
        return ZERO
    return max(ZERO, inv.total_amount - (inv.returned_amount or 0) - (inv.amount_paid - (inv.refunded_amount or 0)))


def _bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "not_due"
    if days_overdue <= 30:
        return "d1_30"
    if days_overdue <= 60:
        return "d31_60"
    if days_overdue <= 90:
        return "d61_90"
    return "d90_plus"


def collection_status(inv: RetailInvoice, on: date) -> str:
    owed = _outstanding(inv)
    if owed <= 0:
        return "paid"
    if inv.due_date and inv.due_date < on:
        return "overdue"
    return "partially_paid" if inv.amount_paid - (inv.refunded_amount or 0) > 0 else "unpaid"


class RetailCreditMixin:
    # ── Register and aging ─────────────────────────────────────────────────

    async def _open_credit_bills(self, company_id: UUID, customer_id: UUID | None = None) -> list[RetailInvoice]:
        """Active credit bills that still have money owing."""
        q = (
            select(RetailInvoice)
            .where(
                RetailInvoice.company_id == company_id, RetailInvoice.payment_mode == "credit",
                RetailInvoice.status == "active",
                RetailInvoice.total_amount - RetailInvoice.returned_amount - RetailInvoice.amount_paid + RetailInvoice.refunded_amount > 0,
            )
            .order_by(RetailInvoice.due_date.asc().nulls_last(), RetailInvoice.invoice_date, RetailInvoice.invoice_number)
        )
        if customer_id:
            q = q.where(RetailInvoice.customer_id == customer_id)
        return (await self.db.execute(q)).scalars().all()

    async def credit_register(
        self, company_id: UUID, on: date, *, customer_id: UUID | None = None, search: str | None = None,
        status: str | None = None, min_days_overdue: int | None = None, max_days_overdue: int | None = None,
        from_date: date | None = None, to_date: date | None = None, min_outstanding: Decimal | None = None,
        include_paid: bool = False,
    ) -> list[dict]:
        q = (
            select(RetailInvoice, RetailCustomer.name, RetailCustomer.mobile)
            .outerjoin(RetailCustomer, RetailCustomer.id == RetailInvoice.customer_id)
            .where(RetailInvoice.company_id == company_id, RetailInvoice.payment_mode == "credit",
                   RetailInvoice.status == "active")
        )
        if customer_id:
            q = q.where(RetailInvoice.customer_id == customer_id)
        if search:
            like = f"%{search.strip()}%"
            q = q.where(or_(RetailInvoice.invoice_number.ilike(like), RetailCustomer.name.ilike(like), RetailCustomer.mobile.like(like)))
        if from_date:
            q = q.where(RetailInvoice.invoice_date >= from_date)
        if to_date:
            q = q.where(RetailInvoice.invoice_date <= to_date)
        rows = []
        for inv, name, mobile in (await self.db.execute(
            q.order_by(RetailInvoice.due_date.asc().nulls_last(), RetailInvoice.invoice_date)
        )).all():
            owed = _outstanding(inv)
            if owed <= 0 and not include_paid:
                continue
            days = (on - inv.due_date).days if inv.due_date else 0
            st = collection_status(inv, on)
            if status and st != status:
                continue
            if min_days_overdue is not None and days < min_days_overdue:
                continue
            if max_days_overdue is not None and days > max_days_overdue:
                continue
            if min_outstanding is not None and owed < min_outstanding:
                continue
            rows.append({
                "invoice_id": inv.id, "invoice_number": inv.invoice_number, "invoice_date": inv.invoice_date,
                "customer_id": inv.customer_id, "customer_name": name, "customer_mobile": mobile,
                "invoice_amount": inv.total_amount - (inv.returned_amount or 0),
                "amount_paid": inv.amount_paid - (inv.refunded_amount or 0),
                "outstanding": owed, "due_date": inv.due_date, "days_overdue": max(days, 0),
                "bucket": _bucket(days) if owed > 0 else None, "status": st,
            })
        return rows

    async def credit_summary(self, company_id: UUID, on: date, from_date: date | None = None, to_date: date | None = None) -> dict:
        open_rows = await self.credit_register(company_id, on)
        aging = {b: ZERO for b in BUCKETS}
        for r in open_rows:
            aging[r["bucket"]] += r["outstanding"]
        overdue = [r for r in open_rows if r["status"] == "overdue"]
        sales_q = select(func.coalesce(func.sum(RetailInvoice.total_amount - RetailInvoice.returned_amount), 0), func.count()).where(
            RetailInvoice.company_id == company_id, RetailInvoice.payment_mode == "credit", RetailInvoice.status == "active",
        )
        coll_q = (
            select(func.coalesce(func.sum(RetailPayment.amount), 0))
            .join(RetailInvoice, RetailInvoice.id == RetailPayment.invoice_id)
            .where(RetailPayment.company_id == company_id, RetailPayment.status == "active", RetailInvoice.payment_mode == "credit")
        )
        if from_date:
            sales_q = sales_q.where(RetailInvoice.invoice_date >= from_date)
            coll_q = coll_q.where(RetailPayment.payment_date >= from_date)
        if to_date:
            sales_q = sales_q.where(RetailInvoice.invoice_date <= to_date)
            coll_q = coll_q.where(RetailPayment.payment_date <= to_date)
        credit_sales, credit_bills = (await self.db.execute(sales_q)).one()
        collected = (await self.db.execute(coll_q)).scalar()
        today = (await self.db.execute(
            select(func.coalesce(func.sum(RetailPayment.amount), 0))
            .join(RetailInvoice, RetailInvoice.id == RetailPayment.invoice_id)
            .where(RetailPayment.company_id == company_id, RetailPayment.status == "active",
                   RetailInvoice.payment_mode == "credit", RetailPayment.payment_date == on)
        )).scalar()
        return {
            "total_outstanding": sum((r["outstanding"] for r in open_rows), ZERO),
            "total_credit_sales": Decimal(credit_sales), "credit_bills": credit_bills,
            "collected_in_period": Decimal(collected), "collections_today": Decimal(today),
            "total_overdue": sum((r["outstanding"] for r in overdue), ZERO),
            "customers_with_outstanding": len({r["customer_id"] for r in open_rows}),
            "overdue_invoices": len(overdue),
            "aging": aging,
        }

    async def customer_aging(self, company_id: UUID, on: date) -> list[dict]:
        by_customer: dict = {}
        for r in await self.credit_register(company_id, on):
            c = by_customer.setdefault(r["customer_id"], {
                "customer_id": r["customer_id"], "customer_name": r["customer_name"], "customer_mobile": r["customer_mobile"],
                "bills": 0, "outstanding": ZERO, "oldest_due": r["due_date"], **{b: ZERO for b in BUCKETS},
            })
            c["bills"] += 1
            c["outstanding"] += r["outstanding"]
            c[r["bucket"]] += r["outstanding"]
            if r["due_date"] and (c["oldest_due"] is None or r["due_date"] < c["oldest_due"]):
                c["oldest_due"] = r["due_date"]
        return sorted(by_customer.values(), key=lambda c: c["outstanding"], reverse=True)

    async def collections(self, company_id: UUID, from_date: date | None = None, to_date: date | None = None,
                          customer_id: UUID | None = None, credit_only: bool = True) -> list[dict]:
        q = (
            select(RetailPayment, RetailInvoice.invoice_number, RetailInvoice.payment_mode, RetailCustomer.name, RetailCustomer.mobile)
            .join(RetailInvoice, RetailInvoice.id == RetailPayment.invoice_id)
            .outerjoin(RetailCustomer, RetailCustomer.id == RetailInvoice.customer_id)
            .where(RetailPayment.company_id == company_id)
        )
        if credit_only:
            q = q.where(RetailInvoice.payment_mode == "credit")
        if from_date:
            q = q.where(RetailPayment.payment_date >= from_date)
        if to_date:
            q = q.where(RetailPayment.payment_date <= to_date)
        if customer_id:
            q = q.where(RetailInvoice.customer_id == customer_id)
        rows = (await self.db.execute(q.order_by(RetailPayment.created_at.desc()).limit(500))).all()
        return [{
            "id": p.id, "receipt_number": p.receipt_number, "batch_ref": p.batch_ref, "payment_date": p.payment_date,
            "amount": p.amount, "mode": p.mode, "reference": p.reference, "status": p.status, "cancel_reason": p.cancel_reason,
            "invoice_id": p.invoice_id, "invoice_number": num, "payment_mode": pm, "customer_name": name, "customer_mobile": mobile,
        } for p, num, pm, name, mobile in rows]

    # ── Collecting money ───────────────────────────────────────────────────

    async def collect_from_customer(
        self, customer_id: UUID, amount: Decimal, mode: str, payment_date: date | None, reference: str | None,
        client_ref: str | None, company_id: UUID, user_id: UUID,
    ) -> UUID:
        """Take one payment from a customer and settle their credit bills,
        oldest due first. Returns the receipt (batch) id."""
        if client_ref:
            done = (await self.db.execute(
                select(RetailPayment.batch_ref).where(RetailPayment.company_id == company_id, RetailPayment.client_ref == client_ref)
            )).scalar_one_or_none()
            if done:
                return done
        customer = (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.id == customer_id, RetailCustomer.company_id == company_id).with_for_update()
        )).scalar_one_or_none()
        if not customer:
            raise BusinessRulesError("NOT_FOUND", "Customer not found")
        bills = await self._open_credit_bills(company_id, customer_id)
        owed = sum((_outstanding(b) for b in bills), ZERO)
        amount = _q(amount)
        if owed <= 0:
            raise BusinessRulesError("NOTHING_OWED", f"{customer.name} has nothing outstanding.")
        if amount > owed:
            raise BusinessRulesError("OVERPAID", f"{customer.name} owes only ₹{owed:,.2f}.")
        batch = uuid4()
        receipt = await self._next_number(RetailPayment, RetailPayment.receipt_number, "RR", company_id)
        now = datetime.now(timezone.utc)
        left, first = amount, True
        settings = await self.get_settings(company_id)
        for bill in bills:
            if left <= 0:
                break
            take = min(left, _outstanding(bill))
            self.db.add(RetailPayment(
                company_id=company_id, invoice_id=bill.id, receipt_number=receipt, batch_ref=batch,
                client_ref=client_ref if first else None, payment_date=payment_date or date.today(), amount=take,
                mode=mode, reference=reference, status="active", created_by=user_id, created_at=now,
            ))
            first = False
            bill.amount_paid += take
            self._refresh_status(bill)
            if bill.payment_status == "paid":
                await self._award_points(bill, customer, settings, user_id)
            left -= take
        await self.db.flush()
        return batch

    @staticmethod
    def _refresh_status(inv: RetailInvoice) -> None:
        net_total = inv.total_amount - (inv.returned_amount or 0)
        kept = inv.amount_paid - (inv.refunded_amount or 0)
        inv.payment_status = "paid" if kept >= net_total else ("partially_paid" if kept > 0 else "unpaid")

    async def receipt(self, batch_ref: UUID, company_id: UUID) -> list[tuple[RetailPayment, RetailInvoice]]:
        rows = (await self.db.execute(
            select(RetailPayment, RetailInvoice)
            .join(RetailInvoice, RetailInvoice.id == RetailPayment.invoice_id)
            .where(RetailPayment.batch_ref == batch_ref, RetailPayment.company_id == company_id)
            .order_by(RetailInvoice.invoice_number)
        )).all()
        return [(p, i) for p, i in rows]

    async def cancel_payment(self, payment_id: UUID, reason: str, company_id: UUID, user_id: UUID) -> RetailPayment:
        """Undo a payment entered by mistake. It stays on record, marked cancelled."""
        pay = (await self.db.execute(
            select(RetailPayment).where(RetailPayment.id == payment_id, RetailPayment.company_id == company_id).with_for_update()
        )).scalar_one_or_none()
        if not pay:
            raise BusinessRulesError("NOT_FOUND", "Payment not found")
        if pay.status != "active":
            raise BusinessRulesError("CANCELLED", "This payment is already cancelled.")
        inv = (await self.db.execute(select(RetailInvoice).where(RetailInvoice.id == pay.invoice_id).with_for_update())).scalar_one()
        if inv.status != "active":
            raise BusinessRulesError("CANCELLED", "The bill is cancelled.")
        if inv.amount_paid - pay.amount < (inv.refunded_amount or 0):
            raise BusinessRulesError("REFUNDED", "Part of this payment was refunded on a return — it can't be cancelled.")
        pay.status, pay.cancel_reason = "cancelled", reason.strip()
        pay.cancelled_at, pay.cancelled_by = datetime.now(timezone.utc), user_id
        inv.amount_paid -= pay.amount
        self._refresh_status(inv)
        if inv.points_awarded and inv.payment_status != "paid" and inv.customer_id:
            # The bill is no longer fully paid, so its points come back off.
            customer = (await self.db.execute(
                select(RetailCustomer).where(RetailCustomer.id == inv.customer_id).with_for_update()
            )).scalar_one()
            kept = inv.points_earned - (inv.points_returned or 0)
            if kept > 0:
                self._add_points(customer, "reversed", -kept, user_id, invoice_id=inv.id,
                                 reason=f"Payment {pay.receipt_number} cancelled — {inv.invoice_number} not fully paid")
            inv.points_awarded = False
        await self.db.flush()
        return pay

    # ── Returns ────────────────────────────────────────────────────────────

    async def returned_qty_by_item(self, invoice_id: UUID) -> dict[UUID, Decimal]:
        rows = (await self.db.execute(
            select(RetailReturnItem.invoice_item_id, func.sum(RetailReturnItem.quantity))
            .join(RetailReturn, RetailReturn.id == RetailReturnItem.return_id)
            .where(RetailReturn.invoice_id == invoice_id)
            .group_by(RetailReturnItem.invoice_item_id)
        )).all()
        return {i: Decimal(q) for i, q in rows}

    async def create_return(self, invoice_id: UUID, body, company_id: UUID, user_id: UUID) -> RetailReturn:
        if body.client_ref:
            done = (await self.db.execute(
                select(RetailReturn.id).where(RetailReturn.company_id == company_id, RetailReturn.client_ref == body.client_ref)
            )).scalar_one_or_none()
            if done:
                return await self.get_return(done, company_id)
        inv = (await self.db.execute(
            select(RetailInvoice).where(RetailInvoice.id == invoice_id, RetailInvoice.company_id == company_id).with_for_update()
        )).scalar_one_or_none()
        if not inv:
            raise BusinessRulesError("NOT_FOUND", "Bill not found")
        if inv.status != "active":
            raise BusinessRulesError("CANCELLED", "This bill is cancelled.")
        items = {i.id: i for i in (await self.db.execute(
            select(RetailInvoiceItem).where(RetailInvoiceItem.invoice_id == inv.id)
        )).scalars().all()}
        returned = await self.returned_qty_by_item(inv.id)
        returned_amt = dict((await self.db.execute(
            select(RetailReturnItem.invoice_item_id, func.sum(RetailReturnItem.amount))
            .join(RetailReturn, RetailReturn.id == RetailReturnItem.return_id)
            .where(RetailReturn.invoice_id == inv.id).group_by(RetailReturnItem.invoice_item_id)
        )).all())
        lines = [l for l in body.items if l.quantity > 0]
        if not lines:
            raise BusinessRulesError("NOTHING_RETURNED", "Enter the quantity being returned.")
        today = body.return_date or date.today()
        now = datetime.now(timezone.utc)
        number = await self._next_number(RetailReturn, RetailReturn.return_number, "RT", company_id)
        ret = RetailReturn(
            company_id=company_id, return_number=number, client_ref=body.client_ref, invoice_id=inv.id,
            customer_id=inv.customer_id, return_date=today, reason=body.reason.strip(),
            return_amount=ZERO, taxable_amount=ZERO, cgst_amount=ZERO, sgst_amount=ZERO,
            refund_mode=body.refund_mode, created_by=user_id, created_at=now,
        )
        self.db.add(ret)
        await self.db.flush()
        total = taxable = cgst = sgst = ZERO
        for line in lines:
            item = items.get(line.invoice_item_id)
            if not item:
                raise BusinessRulesError("NOT_FOUND", "An item on this return isn't on the bill")
            left = item.quantity - returned.get(item.id, ZERO)
            if line.quantity > left:
                raise BusinessRulesError("TOO_MANY", f"Only {left.normalize():f} of {item.description} can still be returned.")
            if line.quantity == left:
                # The last of this line: take whatever is left so rounding can't drift.
                amount = item.net_amount - Decimal(returned_amt.get(item.id) or 0)
            else:
                amount = _q(item.net_amount * line.quantity / item.quantity)
            l_taxable = _q(amount * 100 / (100 + item.gst_rate))
            l_cgst = _q((amount - l_taxable) / 2)
            l_sgst = amount - l_taxable - l_cgst
            txn = await self.inv.receive(ReceiveParams(
                company_id=company_id, product_id=item.product_id, variant_id=item.variant_id,
                warehouse_id=inv.warehouse_id, quantity=line.quantity, unit_id=item.unit_id,
                unit_cost=item.unit_cost, material_type="finished_good", transaction_date=today,
                reference_type="retail_return", reference_id=ret.id, notes=f"Return {number} on {inv.invoice_number}",
            ), user_id=user_id)
            self.db.add(RetailReturnItem(
                return_id=ret.id, invoice_item_id=item.id, product_id=item.product_id, variant_id=item.variant_id,
                description=item.description, quantity=line.quantity, amount=amount, taxable_amount=l_taxable,
                cgst_amount=l_cgst, sgst_amount=l_sgst, unit_cost=item.unit_cost, inv_transaction_id=txn.id,
            ))
            total += amount
            taxable += l_taxable
            cgst += l_cgst
            sgst += l_sgst
            returned[item.id] = returned.get(item.id, ZERO) + line.quantity

        everything_back = all(returned.get(i.id, ZERO) >= i.quantity for i in items.values())
        owed_before = _outstanding(inv)
        new_returned = inv.returned_amount + total
        if everything_back:
            # Whole bill back: the bill's round-off goes with it.
            total += inv.total_amount - new_returned
            new_returned = inv.total_amount
        applied = min(total, owed_before)
        refund = total - applied
        if refund > 0 and not body.refund_mode:
            raise BusinessRulesError("REFUND_MODE", f"₹{refund:,.2f} goes back to the customer — choose how it's refunded.")
        inv.returned_amount = new_returned
        inv.refunded_amount = (inv.refunded_amount or 0) + refund
        ret.return_amount, ret.taxable_amount, ret.cgst_amount, ret.sgst_amount = total, taxable, cgst, sgst
        ret.applied_to_balance, ret.refund_amount = applied, refund
        self._refresh_status(inv)

        # Points earned on the bill shrink with it.
        if inv.points_earned:
            remaining_value = inv.total_amount - inv.returned_amount
            keep = int(Decimal(inv.points_earned) * remaining_value / inv.total_amount) if inv.total_amount else 0
            take_back = (inv.points_earned - (inv.points_returned or 0)) - keep
            if take_back > 0:
                inv.points_returned = (inv.points_returned or 0) + take_back
                ret.points_reversed = take_back
                if inv.points_awarded and inv.customer_id:
                    customer = (await self.db.execute(
                        select(RetailCustomer).where(RetailCustomer.id == inv.customer_id).with_for_update()
                    )).scalar_one()
                    self._add_points(customer, "reversed", -take_back, user_id, invoice_id=inv.id,
                                     reason=f"Return {number} on {inv.invoice_number}")
        if inv.payment_status == "paid" and inv.customer_id and not inv.points_awarded:
            customer = (await self.db.execute(
                select(RetailCustomer).where(RetailCustomer.id == inv.customer_id).with_for_update()
            )).scalar_one()
            await self._award_points(inv, customer, await self.get_settings(company_id), user_id)
        await self.db.flush()
        return await self.get_return(ret.id, company_id)

    async def get_return(self, return_id: UUID, company_id: UUID) -> RetailReturn | None:
        from sqlalchemy.orm import selectinload
        return (await self.db.execute(
            select(RetailReturn).where(RetailReturn.id == return_id, RetailReturn.company_id == company_id)
            .options(selectinload(RetailReturn.items), selectinload(RetailReturn.invoice), selectinload(RetailReturn.customer))
            .execution_options(populate_existing=True)
        )).scalar_one_or_none()

    async def list_returns(self, company_id: UUID, invoice_id: UUID | None = None, search: str | None = None) -> list[RetailReturn]:
        from sqlalchemy.orm import selectinload
        q = (select(RetailReturn).where(RetailReturn.company_id == company_id)
             .options(selectinload(RetailReturn.invoice), selectinload(RetailReturn.customer)))
        if invoice_id:
            q = q.where(RetailReturn.invoice_id == invoice_id)
        if search:
            like = f"%{search.strip()}%"
            q = q.outerjoin(RetailCustomer, RetailCustomer.id == RetailReturn.customer_id).where(
                or_(RetailReturn.return_number.ilike(like), RetailCustomer.name.ilike(like), RetailCustomer.mobile.like(like)))
        return (await self.db.execute(q.order_by(RetailReturn.created_at.desc()).limit(300))).scalars().all()
