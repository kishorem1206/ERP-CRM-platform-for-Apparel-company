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
