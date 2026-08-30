"""PurchaseService: vendor master, purchase orders, and GRN (goods receipt)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import (
    PurchaseEntry, PurchaseEntryItem, PurchaseOrder, PurchaseOrderItem, Vendor,
    VendorBankDetail, VendorContact,
)
from app.schemas.inventory import ReceiveParams
from app.schemas.purchase import (
    GRNItemCreate, POItemCreate, PurchaseEntryCreate, PurchaseOrderCreate,
    PurchaseOrderUpdate, VendorCreate, VendorUpdate,
)
from app.services.inventory import InventoryService


def _compute_item_amounts(
    unit_price: Decimal,
    ordered_qty: Decimal,
    discount_pct: Decimal,
    gst_rate: Decimal,
    intrastate: bool,
) -> dict:
    gross = (unit_price * ordered_qty).quantize(Decimal("0.01"))
    discount_amount = (gross * discount_pct / 100).quantize(Decimal("0.01"))
    taxable = (gross - discount_amount).quantize(Decimal("0.01"))
    half_rate = (gst_rate / 2).quantize(Decimal("0.01"))

    if intrastate:
        cgst = (taxable * half_rate / 100).quantize(Decimal("0.01"))
        sgst = cgst
        igst = Decimal("0")
    else:
        cgst = Decimal("0")
        sgst = Decimal("0")
        igst = (taxable * gst_rate / 100).quantize(Decimal("0.01"))

    total = (taxable + cgst + sgst + igst).quantize(Decimal("0.01"))
    return {
        "discount_amount": discount_amount,
        "taxable_amount": taxable,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "total_amount": total,
    }


async def _next_sequence(db: AsyncSession, prefix: str, company_id: UUID, model_cls, number_field) -> str:
    result = await db.execute(
        select(func.count()).where(getattr(model_cls, "company_id") == company_id)
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:05d}"


class PurchaseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    # ── Vendors ────────────────────────────────────────────────────────────

    async def list_vendors(
        self,
        company_id: UUID,
        active_only: bool = True,
        vendor_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Vendor], int]:
        q = (
            select(Vendor)
            .where(Vendor.company_id == company_id, Vendor.deleted_at.is_(None))
            .options(selectinload(Vendor.contacts), selectinload(Vendor.bank_details))
        )
        if active_only:
            q = q.where(Vendor.is_active.is_(True))
        if vendor_type:
            q = q.where(Vendor.vendor_type == vendor_type)
        if search:
            q = q.where(Vendor.name.ilike(f"%{search}%") | Vendor.code.ilike(f"%{search}%"))

        total_result = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_result.scalar() or 0

        q = q.order_by(Vendor.code).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def get_vendor(self, vendor_id: UUID, company_id: UUID) -> Vendor | None:
        result = await self.db.execute(
            select(Vendor)
            .where(Vendor.id == vendor_id, Vendor.company_id == company_id, Vendor.deleted_at.is_(None))
            .options(selectinload(Vendor.contacts), selectinload(Vendor.bank_details))
        )
        return result.scalar_one_or_none()

    async def create_vendor(self, body: VendorCreate, company_id: UUID, user_id: UUID) -> Vendor:
        now = datetime.now(timezone.utc)
        vendor = Vendor(
            company_id=company_id,
            code=body.code,
            name=body.name,
            gstin=body.gstin,
            pan=body.pan,
            vendor_type=body.vendor_type,
            payment_terms=body.payment_terms,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(vendor)
        await self.db.flush()

        for c in body.contacts:
            self.db.add(VendorContact(vendor_id=vendor.id, **c.model_dump()))
        for b in body.bank_details:
            self.db.add(VendorBankDetail(vendor_id=vendor.id, **b.model_dump()))

        await self.db.flush()

        result = await self.db.execute(
            select(Vendor)
            .where(Vendor.id == vendor.id)
            .options(selectinload(Vendor.contacts), selectinload(Vendor.bank_details))
        )
        return result.scalar_one()

    async def update_vendor(self, vendor_id: UUID, body: VendorUpdate, company_id: UUID) -> Vendor | None:
        vendor = await self.get_vendor(vendor_id, company_id)
        if not vendor:
            return None
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(vendor, field, value)
        vendor.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return vendor

    # ── Purchase Orders ────────────────────────────────────────────────────

    async def list_purchase_orders(
        self,
        company_id: UUID,
        status: str | None = None,
        vendor_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PurchaseOrder], int]:
        q = (
            select(PurchaseOrder)
            .where(PurchaseOrder.company_id == company_id, PurchaseOrder.deleted_at.is_(None))
            .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
        )
        if status:
            q = q.where(PurchaseOrder.status == status)
        if vendor_id:
            q = q.where(PurchaseOrder.vendor_id == vendor_id)

        total_result = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_result.scalar() or 0

        q = q.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def get_purchase_order(self, po_id: UUID, company_id: UUID) -> PurchaseOrder | None:
        result = await self.db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.company_id == company_id, PurchaseOrder.deleted_at.is_(None))
            .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
        )
        return result.scalar_one_or_none()

    async def create_purchase_order(
        self,
        body: PurchaseOrderCreate,
        company_id: UUID,
        user_id: UUID,
    ) -> PurchaseOrder:
        po_number = await _next_sequence(self.db, "PO", company_id, PurchaseOrder, PurchaseOrder.po_number)
        now = datetime.now(timezone.utc)

        po = PurchaseOrder(
            company_id=company_id,
            po_number=po_number,
            vendor_id=body.vendor_id,
            warehouse_id=body.warehouse_id,
            order_date=body.order_date,
            expected_date=body.expected_date,
            notes=body.notes,
            terms=body.terms,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(po)
        await self.db.flush()

        total_taxable = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        total_igst = Decimal("0")
        total_amount = Decimal("0")

        for item_data in body.items:
            amounts = _compute_item_amounts(
                item_data.unit_price,
                item_data.ordered_qty,
                item_data.discount_pct,
                item_data.gst_rate,
                body.intrastate,
            )
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item_data.product_id,
                variant_id=item_data.variant_id,
                unit_id=item_data.unit_id,
                ordered_qty=item_data.ordered_qty,
                unit_price=item_data.unit_price,
                discount_pct=item_data.discount_pct,
                gst_rate=item_data.gst_rate,
                notes=item_data.notes,
                **amounts,
            )
            self.db.add(item)
            total_taxable += amounts["taxable_amount"]
            total_cgst += amounts["cgst_amount"]
            total_sgst += amounts["sgst_amount"]
            total_igst += amounts["igst_amount"]
            total_amount += amounts["total_amount"]

        po.taxable_amount = total_taxable
        po.cgst_amount = total_cgst
        po.sgst_amount = total_sgst
        po.igst_amount = total_igst
        po.total_amount = total_amount

        await self.db.flush()

        result = await self.db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po.id)
            .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
        )
        return result.scalar_one()

    async def update_purchase_order(
        self, po_id: UUID, body: PurchaseOrderUpdate, company_id: UUID
    ) -> PurchaseOrder | None:
        po = await self.get_purchase_order(po_id, company_id)
        if not po or po.status != "draft":
            return None
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(po, field, value)
        po.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return po

    async def approve_purchase_order(self, po_id: UUID, company_id: UUID, user_id: UUID) -> PurchaseOrder | None:
        po = await self.get_purchase_order(po_id, company_id)
        if not po or po.status != "draft":
            return None
        po.status = "approved"
        po.approved_by = user_id
        po.approved_at = datetime.now(timezone.utc)
        po.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return po

    async def cancel_purchase_order(self, po_id: UUID, company_id: UUID) -> PurchaseOrder | None:
        po = await self.get_purchase_order(po_id, company_id)
        if not po or po.status not in ("draft", "approved"):
            return None
        po.status = "cancelled"
        po.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return po

    # ── Purchase Entries (GRN) ─────────────────────────────────────────────

    async def list_purchase_entries(
        self,
        company_id: UUID,
        status: str | None = None,
        vendor_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PurchaseEntry], int]:
        q = (
            select(PurchaseEntry)
            .where(PurchaseEntry.company_id == company_id)
            .options(selectinload(PurchaseEntry.vendor), selectinload(PurchaseEntry.items))
        )
        if status:
            q = q.where(PurchaseEntry.status == status)
        if vendor_id:
            q = q.where(PurchaseEntry.vendor_id == vendor_id)

        total_result = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_result.scalar() or 0

        q = q.order_by(PurchaseEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def get_purchase_entry(self, entry_id: UUID, company_id: UUID) -> PurchaseEntry | None:
        result = await self.db.execute(
            select(PurchaseEntry)
            .where(PurchaseEntry.id == entry_id, PurchaseEntry.company_id == company_id)
            .options(selectinload(PurchaseEntry.vendor), selectinload(PurchaseEntry.items))
        )
        return result.scalar_one_or_none()

    async def create_purchase_entry(
        self,
        body: PurchaseEntryCreate,
        company_id: UUID,
        user_id: UUID,
    ) -> PurchaseEntry:
        entry_number = await _next_sequence(self.db, "GRN", company_id, PurchaseEntry, PurchaseEntry.entry_number)
        now = datetime.now(timezone.utc)

        entry = PurchaseEntry(
            company_id=company_id,
            entry_number=entry_number,
            purchase_order_id=body.purchase_order_id,
            vendor_id=body.vendor_id,
            warehouse_id=body.warehouse_id,
            entry_date=body.entry_date,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            notes=body.notes,
            created_by=user_id,
            created_at=now,
            updated_at=now,
            status="confirmed",
        )
        self.db.add(entry)
        await self.db.flush()

        total_taxable = Decimal("0")
        total_amount = Decimal("0")

        for item_data in body.items:
            item_total = (item_data.accepted_qty * item_data.unit_price).quantize(Decimal("0.01"))

            inv_txn = None
            if item_data.accepted_qty > 0:
                inv_txn = await self.inv.receive(
                    ReceiveParams(
                        company_id=company_id,
                        product_id=item_data.product_id,
                        variant_id=item_data.variant_id,
                        warehouse_id=body.warehouse_id,
                        quantity=item_data.accepted_qty,
                        unit_id=item_data.unit_id,
                        unit_cost=item_data.unit_price,
                        material_type="raw_material",
                        transaction_date=body.entry_date,
                        reference_type="purchase_entry",
                        reference_id=entry.id,
                        notes=f"GRN {entry_number}",
                    ),
                    user_id=user_id,
                )
                await self.db.flush()

            entry_item = PurchaseEntryItem(
                purchase_entry_id=entry.id,
                po_item_id=item_data.po_item_id,
                product_id=item_data.product_id,
                variant_id=item_data.variant_id,
                unit_id=item_data.unit_id,
                received_qty=item_data.received_qty,
                accepted_qty=item_data.accepted_qty,
                rejected_qty=item_data.rejected_qty,
                unit_price=item_data.unit_price,
                total_amount=item_total,
                quality_status=item_data.quality_status,
                notes=item_data.notes,
                inv_transaction_id=inv_txn.id if inv_txn else None,
            )
            self.db.add(entry_item)
            total_taxable += item_total
            total_amount += item_total

            # Update PO item received_qty
            if item_data.po_item_id:
                po_item_result = await self.db.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.id == item_data.po_item_id)
                )
                po_item = po_item_result.scalar_one_or_none()
                if po_item:
                    po_item.received_qty += item_data.accepted_qty

        entry.taxable_amount = total_taxable
        entry.total_amount = total_amount
        await self.db.flush()

        # Update PO status if applicable
        if body.purchase_order_id:
            po_result = await self.db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == body.purchase_order_id)
                .options(selectinload(PurchaseOrder.items))
            )
            po = po_result.scalar_one_or_none()
            if po and po.status in ("approved", "partial"):
                fully_received = all(
                    item.received_qty >= item.ordered_qty for item in po.items
                )
                po.status = "received" if fully_received else "partial"
                po.updated_at = now

        await self.db.flush()

        result = await self.db.execute(
            select(PurchaseEntry)
            .where(PurchaseEntry.id == entry.id)
            .options(selectinload(PurchaseEntry.vendor), selectinload(PurchaseEntry.items))
        )
        return result.scalar_one()
