"""GRN receipts against Purchase Orders.

Builds its scenario inside one transaction and rolls it back, so nothing is
left behind in the database it runs against.
Run from the backend container: python -m pytest tests/test_purchase_grn.py
"""
import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.master import Product, Unit, Warehouse
from app.models.purchase import PurchaseOrderItem, Vendor
from app.models.user import User
from app.schemas.purchase import GRNItemCreate, POItemCreate, PurchaseEntryCreate, PurchaseOrderCreate
from app.services.purchase import PurchaseService


async def _run_multi_po_grn_scenario():
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            vendor = (await db.execute(select(Vendor.id).where(Vendor.company_id == company_id).limit(1))).scalar_one()
            warehouse = (await db.execute(select(Warehouse.id).where(Warehouse.company_id == company_id).limit(1))).scalar_one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            product_a, product_b = (await db.execute(
                select(Product.id).where(Product.company_id == company_id).limit(2)
            )).scalars().all()
            svc = PurchaseService(db)

            async def approved_po(*lines):
                po = await svc.create_purchase_order(
                    PurchaseOrderCreate(
                        vendor_id=vendor, order_date=date.today(),
                        items=[POItemCreate(product_id=p, unit_id=unit, ordered_qty=q, unit_price=10) for p, q in lines],
                    ),
                    company_id, user_id,
                )
                await svc.approve_purchase_order(po.id, company_id, user_id)
                return await svc.get_purchase_order(po.id, company_id)

            finished = await approved_po((product_a, 10))
            part_done = await approved_po((product_a, 10), (product_b, 5))
            untouched = await approved_po((product_b, 7))

            def line(po_line, qty):
                return GRNItemCreate(
                    po_item_id=po_line.id, product_id=po_line.product_id, unit_id=unit,
                    received_qty=qty, accepted_qty=qty, unit_price=10,
                )

            await svc.create_purchase_entry(
                PurchaseEntryCreate(
                    vendor_id=vendor, warehouse_id=warehouse, entry_date=date.today(),
                    items=[line(finished.items[0], 10), line(part_done.items[0], 4)],
                ),
                company_id, user_id,
            )
            part_line_id = part_done.items[0].id
            status = {}
            for name, po in (("finished", finished), ("part_done", part_done), ("untouched", untouched)):
                await db.refresh(po)
                status[name] = po.status
            received = (await db.execute(
                select(PurchaseOrderItem.received_qty).where(PurchaseOrderItem.id == part_line_id)
            )).scalar_one()
            return status, received
        finally:
            await db.rollback()


def test_grn_updates_every_po_it_receives_against():
    status, received = asyncio.run(_run_multi_po_grn_scenario())
    assert status == {"finished": "received", "part_done": "partial", "untouched": "approved"}
    assert received == Decimal("4")


async def _run_grn_edit_scenario():
    """Correcting a GRN moves stock, the PO line and the PO status with it,
    and refuses to take back stock that has already been used."""
    from app.domain.business_rules import BusinessRulesError
    from app.models.master import Warehouse as WarehouseModel
    from app.schemas.inventory import IssueParams
    from app.schemas.purchase import GRNItemUpdate, PurchaseEntryUpdate

    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            vendor = (await db.execute(select(Vendor.id).where(Vendor.company_id == company_id).limit(1))).scalar_one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            product = (await db.execute(select(Product.id).where(Product.company_id == company_id).limit(1))).scalar_one()
            warehouse = WarehouseModel(company_id=company_id, name="GRN edit check store")
            db.add(warehouse)
            await db.flush()
            svc = PurchaseService(db)

            po = await svc.create_purchase_order(
                PurchaseOrderCreate(vendor_id=vendor, order_date=date.today(),
                                    items=[POItemCreate(product_id=product, unit_id=unit, ordered_qty=10, unit_price=10)]),
                company_id, user_id,
            )
            await svc.approve_purchase_order(po.id, company_id, user_id)
            po = await svc.get_purchase_order(po.id, company_id)
            grn = await svc.create_purchase_entry(
                PurchaseEntryCreate(
                    vendor_id=vendor, warehouse_id=warehouse.id, entry_date=date.today(), purchase_order_id=po.id,
                    items=[GRNItemCreate(po_item_id=po.items[0].id, product_id=product, unit_id=unit,
                                         received_qty=10, accepted_qty=10, unit_price=10)],
                ),
                company_id, user_id,
            )
            line_id = grn.items[0].id

            edited = await svc.update_purchase_entry(
                grn.id,
                PurchaseEntryUpdate(invoice_number="INV-77", items=[GRNItemUpdate(id=line_id, received_qty=10, rejected_qty=3, unit_price=12)]),
                company_id, user_id,
            )
            await db.refresh(po)
            stock_after_edit = await svc.inv.get_balance(company_id, product, warehouse.id)
            po_line_received = (await db.execute(
                select(PurchaseOrderItem.received_qty).where(PurchaseOrderItem.purchase_order_id == po.id)
            )).scalar_one()

            # Use 6 of the 7 in stock, then try to cut accepted from 7 to 0.
            await svc.inv.issue(IssueParams(company_id=company_id, product_id=product, warehouse_id=warehouse.id,
                                            quantity=6, unit_id=unit, unit_cost=12, transaction_date=date.today()), user_id)
            refused = None
            try:
                await svc.update_purchase_entry(
                    grn.id, PurchaseEntryUpdate(items=[GRNItemUpdate(id=line_id, received_qty=10, rejected_qty=10, unit_price=12)]),
                    company_id, user_id,
                )
            except BusinessRulesError as e:
                refused = e.code
            return {
                "item": edited.items[0], "total": edited.total_amount, "invoice": edited.invoice_number,
                "po_status": po.status, "po_line_received": po_line_received,
                "stock_after_edit": stock_after_edit, "refused": refused,
            }
        finally:
            await db.rollback()


def test_grn_edit_moves_stock_and_po_and_guards_used_stock():
    r = asyncio.run(_run_grn_edit_scenario())
    assert r["item"].accepted_qty == Decimal("7") and r["item"].rejected_qty == Decimal("3")
    assert r["item"].quality_status == "partial"
    assert r["total"] == Decimal("84.00")          # 7 x 12
    assert r["invoice"] == "INV-77"
    assert r["stock_after_edit"] == Decimal("7")
    assert r["po_line_received"] == Decimal("7") and r["po_status"] == "partial"
    assert r["refused"] == "STOCK_ALREADY_USED"


async def _run_tolerance_close_scenario():
    """Receipts inside a line's ± tolerance close the PO (or let the user
    close it); anything outside needs an admin to approve the close."""
    from app.domain.business_rules import BusinessRulesError
    from app.schemas.purchase import GRNItemUpdate, PurchaseEntryUpdate

    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            vendor = (await db.execute(select(Vendor.id).where(Vendor.company_id == company_id).limit(1))).scalar_one()
            warehouse = (await db.execute(select(Warehouse.id).where(Warehouse.company_id == company_id).limit(1))).scalar_one()
            unit = (await db.execute(select(Unit.id).where(Unit.company_id == company_id).limit(1))).scalar_one()
            product = (await db.execute(select(Product.id).where(Product.company_id == company_id).limit(1))).scalar_one()
            svc = PurchaseService(db)

            async def receive(tolerance, qty):
                po = await svc.create_purchase_order(PurchaseOrderCreate(
                    vendor_id=vendor, order_date=date.today(),
                    items=[POItemCreate(product_id=product, unit_id=unit, ordered_qty=500, unit_price=10, tolerance_pct=tolerance)],
                ), company_id, user_id)
                await svc.approve_purchase_order(po.id, company_id, user_id)
                po_line = (await svc.get_purchase_order(po.id, company_id)).items[0]
                grn = await svc.create_purchase_entry(PurchaseEntryCreate(
                    vendor_id=vendor, warehouse_id=warehouse, entry_date=date.today(),
                    items=[GRNItemCreate(po_item_id=po_line.id, product_id=product, unit_id=unit,
                                         received_qty=qty, accepted_qty=qty, unit_price=10)],
                ), company_id, user_id)
                po_id, grn_id, grn_line = po.id, grn.id, grn.items[0].id
                db.expire_all()
                return po_id, grn_id, grn_line

            async def status(po_id):
                db.expire_all()
                return (await svc.get_purchase_order(po_id, company_id)).status

            async def error(coro):
                try:
                    await coro
                except BusinessRulesError as e:
                    return e.code

            r = {}
            short_ok, _, _ = await receive(10, 480)          # 450-550 allowed
            r["short_ok_after_grn"] = await status(short_ok)
            await svc.close_purchase_order(short_ok, company_id, user_id, None, can_approve=False)
            r["short_ok_closed"] = await status(short_ok)

            within_over, _, _ = await receive(10, 520)
            r["within_over"] = await status(within_over)

            way_over, _, _ = await receive(10, 50000)
            r["way_over"] = await status(way_over)
            await svc.decide_po_close(way_over, company_id, user_id, approve=True)
            r["way_over_approved"] = await status(way_over)

            too_short, _, _ = await receive(10, 300)
            r["too_short_no_reason"] = await error(svc.close_purchase_order(too_short, company_id, user_id, " ", can_approve=False))
            await svc.close_purchase_order(too_short, company_id, user_id, "Vendor out of stock", can_approve=False)
            r["too_short_requested"] = await status(too_short)
            await svc.decide_po_close(too_short, company_id, user_id, approve=False, reason="Chase the rest")
            r["too_short_rejected"] = await status(too_short)
            r["admin_closes_directly"] = (await svc.close_purchase_order(too_short, company_id, user_id, None, can_approve=True)).status

            exact, grn_id, grn_line = await receive(None, 501)  # no tolerance: exact only
            r["exact_over"] = await status(exact)
            await svc.update_purchase_entry(
                grn_id, PurchaseEntryUpdate(items=[GRNItemUpdate(id=grn_line, received_qty=500, rejected_qty=0, unit_price=10)]),
                company_id, user_id,
            )
            db.expire_all()
            fixed = await svc.get_purchase_order(exact, company_id)
            r["exact_after_edit"] = (fixed.status, fixed.close_requested_at)
            return r
        finally:
            await db.rollback()


def test_po_tolerance_decides_who_can_close():
    r = asyncio.run(_run_tolerance_close_scenario())
    assert r["short_ok_after_grn"] == "partial"
    assert r["short_ok_closed"] == "closed"              # within range: user closes it
    assert r["within_over"] == "received"                # 520 of 500 at ±10%
    assert r["way_over"] == "close_requested"            # above 550: admin must approve
    assert r["way_over_approved"] == "closed"
    assert r["too_short_no_reason"] == "REASON_REQUIRED"
    assert r["too_short_requested"] == "close_requested"
    assert r["too_short_rejected"] == "partial"
    assert r["admin_closes_directly"] == "closed"
    assert r["exact_over"] == "close_requested"          # blank tolerance = exact
    assert r["exact_after_edit"] == ("received", None)   # corrected GRN withdraws the request
