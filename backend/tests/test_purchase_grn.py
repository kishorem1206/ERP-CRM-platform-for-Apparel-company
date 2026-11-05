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
