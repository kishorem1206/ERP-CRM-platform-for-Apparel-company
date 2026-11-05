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
