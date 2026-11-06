"""Retail Sales stage 1: GST-inclusive pricing, discount limits, cash and
credit bills, collections, cancellation and estimates. Rolled back.
Run from the backend container: python -m pytest tests/test_retail.py
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domain.business_rules import BusinessRulesError
from app.models.master import Product, Unit
from app.models.user import User
from app.schemas.inventory import ReceiveParams
from app.schemas.retail import (
    RetailCustomerCreate, RetailEstimateConvert, RetailEstimateCreate, RetailInvoiceCreate,
    RetailLineIn, RetailPaymentCreate, RetailSettingsUpdate,
)
from app.services.inventory import InventoryService
from app.services.retail import RetailService


async def _scenario():
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(
                select(User.id, User.company_id).where(User.email == "admin@company.com")
            )).one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            svc = RetailService(db)
            settings = await svc.get_settings(company_id)
            await svc.update_settings(RetailSettingsUpdate(
                min_discount_pct=Decimal("2"), max_discount_pct=Decimal("10"), default_discount_pct=Decimal("0"),
            ), company_id, user_id)
            product = Product(company_id=company_id, code=f"RT-{uuid4().hex[:6]}", name="Retail Test Tee",
                              product_type="finished_good", unit_id=unit, mrp=Decimal("1050"))
            db.add(product)
            await db.flush()
            await InventoryService(db).receive(ReceiveParams(
                company_id=company_id, product_id=product.id, warehouse_id=settings.warehouse_id, quantity=Decimal("10"),
                unit_id=unit, unit_cost=Decimal("400"), transaction_date=date.today(),
            ), user_id=user_id)
            stock = lambda: InventoryService(db).get_balance(company_id, product.id, settings.warehouse_id)
            customer = await svc.create_customer(RetailCustomerCreate(name="Anitha", mobile="+91 98765 43210"), company_id, user_id)
            r = {"mobile": customer.mobile}

            async def code(coro):
                try:
                    await coro
                except BusinessRulesError as e:
                    return e.code

            r["dup_mobile"] = await code(svc.create_customer(RetailCustomerCreate(name="X", mobile="9876543210"), company_id, user_id))
            line = lambda q, d="0": RetailLineIn(product_id=product.id, quantity=Decimal(q), item_discount_pct=Decimal(d))

            # Cash bill: 2 x ₹1050 with 5% item + 5% bill discount
            ref = uuid4().hex
            cash = await svc.create_invoice(RetailInvoiceCreate(
                client_ref=ref, customer_id=customer.id, payment_mode="cash",
                bill_discount_pct=Decimal("5"), items=[line("2", "5")],
            ), company_id, user_id, can_approve=False)
            r["cash"] = (cash.gross_amount, cash.total_amount, cash.taxable_amount, cash.cgst_amount + cash.sgst_amount,
                         cash.payment_status, cash.amount_paid, len(cash.payments))
            again = await svc.create_invoice(RetailInvoiceCreate(
                client_ref=ref, customer_id=customer.id, items=[line("2", "5")], bill_discount_pct=Decimal("5"),
            ), company_id, user_id, can_approve=False)
            r["same_bill"] = again.id == cash.id
            r["stock_after_cash"] = await stock()

            r["too_low"] = await code(svc.create_invoice(RetailInvoiceCreate(items=[line("1", "1")]), company_id, user_id, False))
            r["too_high"] = await code(svc.create_invoice(RetailInvoiceCreate(items=[line("1", "15")]), company_id, user_id, False))
            approved = await svc.create_invoice(RetailInvoiceCreate(items=[line("1", "15")]), company_id, user_id, True)
            r["approved"] = approved.discount_approved_by == user_id
            r["credit_walkin"] = await code(svc.create_invoice(RetailInvoiceCreate(payment_mode="credit", items=[line("1")]), company_id, user_id, False))
            r["no_stock"] = await code(svc.create_invoice(RetailInvoiceCreate(items=[line("50")]), company_id, user_id, False))

            # Credit bill with part payment, then collections
            credit = await svc.create_invoice(RetailInvoiceCreate(
                customer_id=customer.id, payment_mode="credit", amount_paid_now=Decimal("500"), items=[line("2")],
            ), company_id, user_id, False)
            r["credit"] = (credit.total_amount, credit.payment_status, credit.due_date == date.today() + timedelta(days=settings.credit_days))
            credit_id = credit.id
            r["overpay"] = await code(svc.record_payment(credit_id, RetailPaymentCreate(amount=Decimal("5000")), company_id, user_id))
            pref = uuid4().hex
            await svc.record_payment(credit_id, RetailPaymentCreate(client_ref=pref, amount=Decimal("1000")), company_id, user_id)
            await svc.record_payment(credit_id, RetailPaymentCreate(client_ref=pref, amount=Decimal("1000")), company_id, user_id)
            paid = await svc.record_payment(credit_id, RetailPaymentCreate(amount=Decimal("600")), company_id, user_id)
            r["collected"] = (paid.amount_paid, paid.payment_status, len([p for p in paid.payments if p.status == "active"]))

            stats = (await svc.customer_stats(company_id, [customer.id]))[customer.id]
            r["stats"] = (stats["purchase_count"], stats["total_spent"], stats["products_purchased"], stats["outstanding"])

            before_cancel = await stock()
            cancelled = await svc.cancel_invoice(credit_id, "Customer returned", company_id, user_id)
            r["cancel"] = (cancelled.status, cancelled.amount_paid, await stock() - before_cancel)

            # Estimate -> bill
            est = await svc.save_estimate(RetailEstimateCreate(customer_id=customer.id, items=[line("1")]), company_id, user_id, False)
            r["est_status"] = RetailService.estimate_status(est)
            bill = await svc.convert_estimate(est.id, RetailEstimateConvert(payment_mode="cash"), company_id, user_id, False)
            est = await svc.get_estimate(est.id, company_id)
            r["converted"] = (est.status, est.converted_invoice_id == bill.id, bill.total_amount)
            r["convert_twice"] = await code(svc.convert_estimate(est.id, RetailEstimateConvert(), company_id, user_id, False))
            old = await svc.save_estimate(RetailEstimateCreate(
                estimate_date=date.today() - timedelta(days=10), valid_until=date.today() - timedelta(days=1), items=[line("1")],
            ), company_id, user_id, False)
            r["expired"] = (RetailService.estimate_status(old),
                            await code(svc.convert_estimate(old.id, RetailEstimateConvert(), company_id, user_id, False)))
            r["numbers"] = (cash.invoice_number[:2], est.estimate_number[:2], cash.payments[0].receipt_number[:2])

            # A product with sizes can still sell stock recorded without a size,
            # but only up to that unsized stock.
            from app.models.master import ProductVariant
            db.add(ProductVariant(product_id=product.id, sku=f"RT-{uuid4().hex[:6]}-M", is_active=True))
            await db.flush()
            unsized_left = await stock()
            sold = await svc.create_invoice(RetailInvoiceCreate(items=[line("1")]), company_id, user_id, False)
            r["unsized_sale"] = (sold.items[0].variant_id, unsized_left - await stock())
            r["unsized_too_many"] = await code(svc.create_invoice(RetailInvoiceCreate(items=[line("99")]), company_id, user_id, False))
            hits = await svc.search_products(company_id, "Retail Test Tee")
            r["search"] = sorted((h["variant_id"] is None, h["in_stock"]) for h in hits)
            return r
        finally:
            await db.rollback()


def test_retail_billing_end_to_end():
    r = asyncio.run(_scenario())
    assert r["mobile"] == "9876543210"
    assert r["dup_mobile"] == "DUPLICATE_MOBILE"
    # 2100 MRP, -5% item = 1995, -5% bill = 1895.25 -> rounded 1895; GST 5% backed out
    gross, total, taxable, gst, status, paid, n_pay = r["cash"]
    assert gross == Decimal("2100.00") and total == Decimal("1895")
    assert taxable == Decimal("1805.00") and gst == Decimal("90.25")
    assert (status, paid, n_pay) == ("paid", Decimal("1895"), 1)
    assert r["same_bill"]
    assert r["stock_after_cash"] == Decimal("8")
    assert r["too_low"] == "DISCOUNT_TOO_LOW" and r["too_high"] == "DISCOUNT_TOO_HIGH" and r["approved"]
    assert r["credit_walkin"] == "CUSTOMER_REQUIRED"
    assert r["no_stock"] == "INSUFFICIENT_STOCK"
    assert r["credit"] == (Decimal("2100"), "partially_paid", True)
    assert r["overpay"] == "OVERPAID"
    assert r["collected"] == (Decimal("2100.00"), "paid", 3)          # 500 + 1000 (once) + 600
    assert r["stats"] == (2, Decimal("3995.00"), Decimal("4.000"), Decimal("0.00"))
    assert r["cancel"] == ("cancelled", Decimal("0"), Decimal("2"))
    assert r["est_status"] == "draft"
    assert r["converted"] == ("converted", True, Decimal("1050"))
    assert r["convert_twice"] == "LOCKED"
    assert r["expired"] == ("expired", "EXPIRED")
    assert r["numbers"] == ("RI", "RE", "RR")
    assert r["unsized_sale"] == (None, Decimal("1"))
    assert r["unsized_too_many"] == "INSUFFICIENT_STOCK"
    assert r["search"] == [(False, Decimal("0")), (True, Decimal("5"))]   # size row + unsized stock row (10 in, 5 billed net)


async def _engagement_scenario():
    from app.models.retail import RetailLoyaltyEntry
    from app.schemas.retail import RetailCouponIn

    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(
                select(User.id, User.company_id).where(User.email == "admin@company.com")
            )).one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            svc = RetailService(db)
            settings = await svc.get_settings(company_id)
            await svc.update_settings(RetailSettingsUpdate(
                min_discount_pct=Decimal("0"), max_discount_pct=Decimal("10"),
                loyalty_enabled=True, amount_per_point=Decimal("100"), point_value=Decimal("1"),
                min_redeem_points=10, max_redeem_pct=Decimal("20"), points_expiry_days=30, min_bill_for_points=Decimal("0"),
                birthday_enabled=True, birthday_discount_type="percent", birthday_discount_value=Decimal("15"),
                birthday_window="week", birthday_lead_days=7,
            ), company_id, user_id)
            product = Product(company_id=company_id, code=f"RT-{uuid4().hex[:6]}", name="Retail Loyalty Tee",
                              product_type="finished_good", unit_id=unit, mrp=Decimal("1050"))
            db.add(product)
            await db.flush()
            await InventoryService(db).receive(ReceiveParams(
                company_id=company_id, product_id=product.id, warehouse_id=settings.warehouse_id, quantity=Decimal("30"),
                unit_id=unit, unit_cost=Decimal("400"), transaction_date=date.today(),
            ), user_id=user_id)
            today = date.today()
            anitha = await svc.create_customer(RetailCustomerCreate(
                name="Anitha", mobile="9800000001", date_of_birth=date(1990, *(today + timedelta(days=3)).timetuple()[1:3]),
            ), company_id, user_id)
            ravi = await svc.create_customer(RetailCustomerCreate(name="Ravi", mobile="9800000002"), company_id, user_id)
            line = lambda q: RetailLineIn(product_id=product.id, quantity=Decimal(q))
            r = {}

            async def code(coro):
                try:
                    await coro
                except BusinessRulesError as e:
                    return e.code

            bill = lambda **kw: svc.create_invoice(RetailInvoiceCreate(**kw), company_id, user_id, False)

            # Earn on a cash bill: ₹2100 -> 21 points
            b1 = await bill(customer_id=anitha.id, items=[line("2")])
            r["earn"] = (b1.points_earned, b1.points_awarded, anitha.loyalty_points)

            # Coupon: 10% capped at ₹150 above ₹1000, once per customer
            await svc.save_coupon(RetailCouponIn(
                code="diwali10", name="Diwali", discount_type="percent", discount_value=Decimal("10"),
                min_purchase=Decimal("1000"), max_discount=Decimal("150"), start_date=today, expiry_date=today + timedelta(days=5),
                per_customer_limit=1,
            ), company_id, user_id)
            b2 = await bill(customer_id=anitha.id, coupon_code="DIWALI10", items=[line("2")])
            r["coupon"] = (b2.coupon_discount, b2.total_amount, b2.taxable_amount + b2.cgst_amount + b2.sgst_amount + b2.round_off)
            r["coupon_again"] = await code(bill(customer_id=anitha.id, coupon_code="DIWALI10", items=[line("2")]))
            r["coupon_min"] = await code(bill(customer_id=ravi.id, coupon_code="DIWALI10", items=[RetailLineIn(product_id=product.id, quantity=Decimal("0.5"))]))
            r["coupon_bad"] = await code(bill(coupon_code="NOPE", items=[line("1")]))
            await svc.save_coupon(RetailCouponIn(
                code="OLD5", name="Old", discount_type="fixed", discount_value=Decimal("50"),
                start_date=today - timedelta(days=10), expiry_date=today - timedelta(days=1),
            ), company_id, user_id)
            r["coupon_expired"] = await code(bill(coupon_code="OLD5", items=[line("1")]))

            # Redeem: balance 21 + 19 = 40
            r["balance"] = anitha.loyalty_points
            r["too_many"] = await code(bill(customer_id=anitha.id, redeem_points=300, items=[line("1")]))
            r["below_min"] = await code(bill(customer_id=anitha.id, redeem_points=5, items=[line("1")]))
            b3 = await bill(customer_id=anitha.id, redeem_points=20, items=[line("1")])
            r["redeem"] = (b3.points_discount, b3.total_amount, b3.points_earned, anitha.loyalty_points)   # 1030 -> earns 10
            r["cap"] = await code(bill(customer_id=anitha.id, redeem_points=30, items=[RetailLineIn(product_id=product.id, quantity=Decimal("0.1"))]))

            # Credit bill earns only once paid in full
            b4 = await bill(customer_id=ravi.id, payment_mode="credit", items=[line("1")])
            r["credit_before"] = (b4.points_awarded, ravi.loyalty_points)
            await svc.record_payment(b4.id, RetailPaymentCreate(amount=Decimal("1050")), company_id, user_id)
            r["credit_after"] = ravi.loyalty_points

            # Cancelling the redeem bill: give back 20, take back 10
            await svc.cancel_invoice(b3.id, "test", company_id, user_id)
            r["after_cancel"] = anitha.loyalty_points

            # Expiry: pretend the first 21 points expired yesterday
            first = (await db.execute(select(RetailLoyaltyEntry).where(
                RetailLoyaltyEntry.customer_id == anitha.id, RetailLoyaltyEntry.entry_type == "earned"
            ).order_by(RetailLoyaltyEntry.created_at))).scalars().first()
            first.expires_on = today - timedelta(days=1)
            await db.flush()
            expired = await svc.expire_points(anitha)
            r["expired"] = (expired, anitha.loyalty_points, await svc.expire_points(anitha))

            # Birthday coupon: made once, only for Anitha
            made = await svc.generate_birthday_coupons(company_id)
            again = await svc.generate_birthday_coupons(company_id)
            dash = await svc.birthday_dashboard(company_id)
            bday_code = next(row["coupon_code"] for row in dash["next_7"] if row["customer_id"] == anitha.id)
            r["birthday"] = (made >= 1, again, bday_code.startswith("BDAY-"))
            r["bday_other"] = await code(bill(customer_id=ravi.id, coupon_code=bday_code, items=[line("1")]))
            b5 = await bill(customer_id=anitha.id, coupon_code=bday_code, items=[line("1")])
            r["bday_used"] = (b5.coupon_discount, (await svc.birthday_dashboard(company_id))["coupons_redeemed"] >= 1)
            summary = await svc.loyalty_summary(company_id)
            r["summary"] = summary["points_outstanding"] >= anitha.loyalty_points + ravi.loyalty_points
            return r
        finally:
            await db.rollback()


def test_retail_coupons_loyalty_birthdays():
    r = asyncio.run(_engagement_scenario())
    assert r["earn"] == (21, True, 21)
    assert r["coupon"] == (Decimal("150.00"), Decimal("1950"), Decimal("1950.00"))   # GST still adds up
    assert r["coupon_again"] == "COUPON_LIMIT"
    assert r["coupon_min"] == "COUPON_MIN_PURCHASE"
    assert r["coupon_bad"] == "COUPON_INVALID" and r["coupon_expired"] == "COUPON_EXPIRED"
    assert r["balance"] == 40
    assert r["too_many"] == "NOT_ENOUGH_POINTS" and r["below_min"] == "BELOW_MIN_POINTS"
    assert r["redeem"] == (Decimal("20.00"), Decimal("1030"), 10, 30)
    assert r["cap"] == "TOO_MANY_POINTS"                 # 20% of ₹105 is ₹21
    assert r["credit_before"] == (False, 0) and r["credit_after"] == 10
    assert r["after_cancel"] == 40
    assert r["expired"] == (21, 19, 0)                   # 21 earned early; the 20 redeemed were given back -> all 21 lapse
    assert r["birthday"] == (True, 0, True)
    assert r["bday_other"] == "COUPON_NOT_YOURS"
    assert r["bday_used"] == (Decimal("157.50"), True)   # 15% of ₹1050
    assert r["summary"]


async def _credit_scenario():
    from app.schemas.retail import RetailReturnCreate, RetailReturnLineIn

    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(
                select(User.id, User.company_id).where(User.email == "admin@company.com")
            )).one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            svc = RetailService(db)
            settings = await svc.get_settings(company_id)
            await svc.update_settings(RetailSettingsUpdate(
                min_discount_pct=Decimal("0"), max_discount_pct=Decimal("10"), credit_days=30,
                loyalty_enabled=True, amount_per_point=Decimal("100"), point_value=Decimal("1"), points_expiry_days=0,
                min_bill_for_points=Decimal("0"),
            ), company_id, user_id)
            product = Product(company_id=company_id, code=f"RT-{uuid4().hex[:6]}", name="Retail Credit Tee",
                              product_type="finished_good", unit_id=unit, mrp=Decimal("1000"))
            db.add(product)
            await db.flush()
            await InventoryService(db).receive(ReceiveParams(
                company_id=company_id, product_id=product.id, warehouse_id=settings.warehouse_id, quantity=Decimal("20"),
                unit_id=unit, unit_cost=Decimal("400"), transaction_date=date.today() - timedelta(days=60),
            ), user_id=user_id)
            pid, wh = product.id, settings.warehouse_id
            stock = lambda: InventoryService(db).get_balance(company_id, pid, wh)
            today = date.today()
            cust = await svc.create_customer(RetailCustomerCreate(name="Kavya", mobile="9700000001"), company_id, user_id)
            cust_id = cust.id
            line = lambda q: RetailLineIn(product_id=pid, quantity=Decimal(q))
            r = {}

            async def code(coro):
                try:
                    await coro
                except BusinessRulesError as e:
                    return e.code

            b1 = await svc.create_invoice(RetailInvoiceCreate(customer_id=cust_id, payment_mode="credit",
                                                              invoice_date=today - timedelta(days=40), items=[line("2")]), company_id, user_id, False)
            b2 = await svc.create_invoice(RetailInvoiceCreate(customer_id=cust_id, payment_mode="credit", items=[line("1")]), company_id, user_id, False)
            b1_id, b2_id = b1.id, b2.id
            s = await svc.credit_summary(company_id, today)
            mine = [x for x in await svc.credit_register(company_id, today, customer_id=cust_id)]
            r["register"] = sorted((x["invoice_number"] == b1.invoice_number, x["status"], x["days_overdue"], x["bucket"], x["outstanding"]) for x in mine)
            r["summary_has"] = s["total_outstanding"] >= Decimal("3000") and s["overdue_invoices"] >= 1

            # One collection over both bills, oldest first, one receipt
            batch = await svc.collect_from_customer(cust_id, Decimal("2500"), "upi", None, "UPI-1", "c-1", company_id, user_id)
            again = await svc.collect_from_customer(cust_id, Decimal("2500"), "upi", None, "UPI-1", "c-1", company_id, user_id)
            receipt = await svc.receipt(batch, company_id)
            r["receipt"] = (batch == again, len(receipt), len({p.receipt_number for p, _ in receipt}),
                            sorted(p.amount for p, _ in receipt))
            receipt = [(p.id, i.id) for p, i in receipt]
            db.expire_all()
            b1 = await svc.get_invoice(b1_id, company_id)
            r["b1_paid"] = (b1.payment_status, b1.points_awarded)
            r["overpay"] = await code(svc.collect_from_customer(cust_id, Decimal("1000"), "cash", None, None, None, company_id, user_id))

            # Return the item on b2 (owes ₹500): ₹500 off the balance, ₹500 refunded
            stock_before = await stock()
            item2 = (await svc.get_invoice(b2_id, company_id)).items[0]
            ret = await svc.create_return(b2_id, RetailReturnCreate(
                items=[RetailReturnLineIn(invoice_item_id=item2.id, quantity=Decimal("1"))], reason="Size issue", refund_mode="cash",
            ), company_id, user_id)
            ret_vals = (ret.return_amount, ret.applied_to_balance, ret.refund_amount)
            ret_no = ret.return_number[:2]
            db.expire_all()
            b2 = await svc.get_invoice(b2_id, company_id)
            r["return_b2"] = (*ret_vals, b2.payment_status, await stock() - stock_before, ret_no)

            # Return 1 of 2 on b1 (fully paid, points given): all refunded, half the points back
            pts_before = (await svc.get_customer(cust_id, company_id)).loyalty_points
            item1_id = (await svc.get_invoice(b1_id, company_id)).items[0].id
            ret1 = await svc.create_return(b1_id, RetailReturnCreate(
                items=[RetailReturnLineIn(invoice_item_id=item1_id, quantity=Decimal("1"))], reason="Damaged", refund_mode="cash",
            ), company_id, user_id)
            ret1_vals = (ret1.refund_amount, ret1.points_reversed)
            db.expire_all()
            pts_after = (await svc.get_customer(cust_id, company_id)).loyalty_points
            r["return_b1"] = (*ret1_vals, pts_before - pts_after)
            r["too_many"] = await code(svc.create_return(b1_id, RetailReturnCreate(
                items=[RetailReturnLineIn(invoice_item_id=item1_id, quantity=Decimal("2"))], reason="x x", refund_mode="cash",
            ), company_id, user_id))

            # The b1 collection payment can't be cancelled now — part of it was refunded
            b1_pay_id = next(pid_ for pid_, iid in receipt if iid == b1_id)
            r["cancel_refunded"] = await code(svc.cancel_payment(b1_pay_id, "wrong entry", company_id, user_id))

            # Cancelling b1 puts back only what wasn't already returned
            before = await stock()
            await svc.cancel_invoice(b1_id, "test", company_id, user_id)
            r["cancel_stock"] = await stock() - before

            # A mistaken cash payment can be cancelled
            b3 = await svc.create_invoice(RetailInvoiceCreate(customer_id=cust_id, items=[line("1")]), company_id, user_id, False)
            b3_id = b3.id
            pay = await svc.cancel_payment(b3.payments[0].id, "card declined", company_id, user_id)
            pay_status = pay.status
            db.expire_all()
            b3 = await svc.get_invoice(b3_id, company_id)
            r["cash_cancel"] = (pay_status, b3.payment_status, b3.total_amount - b3.amount_paid)
            stats = (await svc.customer_stats(company_id, [cust_id]))[cust_id]
            r["stats"] = (stats["total_spent"], stats["products_purchased"])
            return r
        finally:
            await db.rollback()


def test_retail_credit_collections_and_returns():
    r = asyncio.run(_credit_scenario())
    assert r["register"] == [(False, "unpaid", 0, "not_due", Decimal("1000")), (True, "overdue", 10, "d1_30", Decimal("2000"))]
    assert r["summary_has"]
    assert r["receipt"] == (True, 2, 1, [Decimal("500.00"), Decimal("2000.00")])
    assert r["b1_paid"] == ("paid", True)
    assert r["overpay"] == "OVERPAID"
    assert r["return_b2"] == (Decimal("1000.00"), Decimal("500.00"), Decimal("500.00"), "paid", Decimal("1"), "RT")
    assert r["return_b1"] == (Decimal("1000.00"), 10, 10)
    assert r["too_many"] == "TOO_MANY"
    assert r["cancel_refunded"] == "REFUNDED"
    assert r["cancel_stock"] == Decimal("1")
    assert r["cash_cancel"] == ("cancelled", "unpaid", Decimal("1000"))
    # b1 cancelled (0); b2 fully returned (0); b3 ₹1000 -> spent 1000, 1 item
    assert r["stats"] == (Decimal("1000.00"), Decimal("1.000"))
