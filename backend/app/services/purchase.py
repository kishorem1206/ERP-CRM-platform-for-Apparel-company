"""PurchaseService: vendor master, purchase orders, and GRN (goods receipt)."""
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.business_rules import BusinessRulesError
from app.models.inventory import InventoryTransaction
from app.models.purchase import (
    BUILTIN_VENDOR_TYPES, PurchaseEntry, PurchaseEntryItem, PurchaseOrder, PurchaseOrderItem, Vendor,
    VendorBankDetail, VendorContact, VendorType,
)
from app.schemas.inventory import ReceiveParams
from app.schemas.purchase import (
    GRNItemCreate, POItemCreate, PurchaseEntryCreate, PurchaseEntryUpdate, PurchaseOrderCreate,
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



# ── Receipt tolerance ────────────────────────────────────────────────────────
# A PO line may be received anywhere within ± tolerance_pct of its ordered
# quantity. Outside that range (short or over) the PO can only be closed once
# an admin approves. Internal only — never printed on the PO / GRN PDFs.

def tolerance_range(item: PurchaseOrderItem) -> tuple[Decimal, Decimal]:
    tol = (item.tolerance_pct or Decimal("0")) / 100
    return item.ordered_qty * (1 - tol), item.ordered_qty * (1 + tol)


def line_tolerance_state(item: PurchaseOrderItem) -> str:
    """"short", "within" or "over" the line's tolerance range."""
    low, high = tolerance_range(item)
    received = item.received_qty or Decimal("0")
    if received > high:
        return "over"
    if received < low:
        return "short"
    return "within"


def _receipt_status(po: PurchaseOrder) -> str:
    """A PO's status from what it has received so far: any line above its
    range waits for an admin to approve closing; every line at least fully
    received (and none over) closes it; otherwise it's part-received."""
    if any(line_tolerance_state(i) == "over" for i in po.items):
        return "close_requested"
    if all((i.received_qty or 0) >= i.ordered_qty for i in po.items):
        return "received"
    if any((i.received_qty or 0) > 0 for i in po.items):
        return "partial"
    return "approved"


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

    # ── Vendor types ──────────────────────────────────────────────────────

    async def list_vendor_types(self, company_id: UUID) -> list[dict]:
        """Built-in types first, then the company's own, by name."""
        custom = (await self.db.execute(
            select(VendorType).where(VendorType.company_id == company_id).order_by(VendorType.name)
        )).scalars().all()
        return [{"code": c, "name": n, "builtin": True} for c, n in BUILTIN_VENDOR_TYPES.items()] + [
            {"code": t.code, "name": t.name, "builtin": False} for t in custom
        ]

    async def create_vendor_type(self, name: str, company_id: UUID) -> dict:
        name = " ".join(name.split())
        if not name:
            raise BusinessRulesError("NAME_REQUIRED", "Type name is required")
        existing = await self.list_vendor_types(company_id)
        if any(t["name"].lower() == name.lower() for t in existing):
            raise BusinessRulesError("DUPLICATE_NAME", f"A vendor type called “{name}” already exists")
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:20] or "type"
        codes = {t["code"] for t in existing}
        code, n = base, 2
        while code in codes:
            suffix = f"_{n}"
            code, n = base[: 20 - len(suffix)] + suffix, n + 1
        self.db.add(VendorType(company_id=company_id, code=code, name=name, created_at=datetime.now(timezone.utc)))
        await self.db.flush()
        return {"code": code, "name": name, "builtin": False}

    async def _check_vendor_type(self, code: str, company_id: UUID) -> None:
        if code in BUILTIN_VENDOR_TYPES:
            return
        found = (await self.db.execute(
            select(VendorType.id).where(VendorType.company_id == company_id, VendorType.code == code)
        )).scalar_one_or_none()
        if not found:
            raise BusinessRulesError("UNKNOWN_VENDOR_TYPE", f"Unknown vendor type “{code}”")

    def _set_contacts_and_banks(self, vendor_id: UUID, contacts, banks) -> None:
        """Add contact / bank rows, skipping blank ones; exactly one of each
        is primary (the first, unless one was marked)."""
        def primary_index(rows) -> int:
            return next((i for i, r in enumerate(rows) if r.is_primary), 0)

        if contacts is not None:
            rows = [c for c in contacts if c.name.strip()]
            first = primary_index(rows)
            for i, c in enumerate(rows):
                data = {k: (v.strip() or None) if isinstance(v, str) else v for k, v in c.model_dump().items()}
                data["name"] = c.name.strip()
                data["is_primary"] = i == first
                self.db.add(VendorContact(vendor_id=vendor_id, **data))
        if banks is not None:
            rows = [b for b in banks if (b.bank_name or "").strip() or (b.account_number or "").strip()]
            first = primary_index(rows)
            for i, b in enumerate(rows):
                data = {k: (v.strip() or None) if isinstance(v, str) else v for k, v in b.model_dump().items()}
                if data.get("ifsc"):
                    data["ifsc"] = data["ifsc"].upper()
                data["is_primary"] = i == first
                self.db.add(VendorBankDetail(vendor_id=vendor_id, **data))

    async def create_vendor(self, body: VendorCreate, company_id: UUID, user_id: UUID) -> Vendor:
        await self._check_vendor_type(body.vendor_type, company_id)
        now = datetime.now(timezone.utc)
        vendor = Vendor(
            company_id=company_id,
            code=body.code,
            name=body.name,
            gstin=body.gstin,
            pan=body.pan,
            vendor_type=body.vendor_type,
            payment_terms=body.payment_terms,
            supplies_product_types=body.supplies_product_types or None,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(vendor)
        await self.db.flush()

        self._set_contacts_and_banks(vendor.id, body.contacts, body.bank_details)
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
        updates = body.model_dump(exclude_unset=True, exclude={"contacts", "bank_details"})
        if updates.get("vendor_type"):
            await self._check_vendor_type(updates["vendor_type"], company_id)
        for field, value in updates.items():
            setattr(vendor, field, value)
        fields = body.model_fields_set
        if "contacts" in fields and body.contacts is not None:
            await self.db.execute(delete(VendorContact).where(VendorContact.vendor_id == vendor.id))
        if "bank_details" in fields and body.bank_details is not None:
            await self.db.execute(delete(VendorBankDetail).where(VendorBankDetail.vendor_id == vendor.id))
        self._set_contacts_and_banks(
            vendor.id,
            body.contacts if "contacts" in fields else None,
            body.bank_details if "bank_details" in fields else None,
        )
        vendor.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        self.db.expire(vendor)
        return await self.get_vendor(vendor_id, company_id)

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
                tolerance_pct=item_data.tolerance_pct,
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

    def _apply_receipt_status(self, po: PurchaseOrder, user_id: UUID | None, now: datetime) -> None:
        """Set the PO's status from its receipts. Going above a line's
        tolerance raises a close request for an admin; coming back inside
        (e.g. a corrected GRN) withdraws it."""
        status = _receipt_status(po)
        if status == "close_requested" and po.status != "close_requested":
            po.close_reason = "Received above the tolerance limit"
            po.close_requested_by = user_id
            po.close_requested_at = now
        elif status != "close_requested" and po.status == "close_requested":
            po.close_reason = po.close_requested_by = po.close_requested_at = None
        po.status = status
        po.updated_at = now

    async def close_purchase_order(
        self, po_id: UUID, company_id: UUID, user_id: UUID, reason: str | None, can_approve: bool,
    ) -> PurchaseOrder | None:
        """Close an approved / part-received PO. Every line within its
        tolerance range closes it straight away; otherwise it needs an admin
        — a user who may approve closes it, anyone else raises a request."""
        po = await self.get_purchase_order(po_id, company_id)
        if not po:
            return None
        if po.status not in ("approved", "partial"):
            raise BusinessRulesError("PO_NOT_OPEN", "Only an approved or part-received PO can be closed.")
        now = datetime.now(timezone.utc)
        within = all(line_tolerance_state(i) == "within" for i in po.items)
        if within or can_approve:
            po.status = "closed"
            po.closed_by = user_id
            po.closed_at = now
            po.close_reason = (reason or "").strip() or None
        else:
            if not (reason or "").strip():
                raise BusinessRulesError(
                    "REASON_REQUIRED", "Some lines are outside their tolerance — give a reason for the admin.",
                )
            po.status = "close_requested"
            po.close_reason = reason.strip()
            po.close_requested_by = user_id
            po.close_requested_at = now
        po.updated_at = now
        await self.db.flush()
        return po

    async def decide_po_close(
        self, po_id: UUID, company_id: UUID, user_id: UUID, approve: bool, reason: str | None = None,
    ) -> PurchaseOrder | None:
        """Admin decision on a close request: approve closes the PO; reject
        reopens it for more receipts (a corrected GRN can also clear it)."""
        po = await self.get_purchase_order(po_id, company_id)
        if not po:
            return None
        if po.status != "close_requested":
            raise BusinessRulesError("NO_CLOSE_REQUEST", "This PO isn't waiting for close approval.")
        now = datetime.now(timezone.utc)
        if approve:
            po.status = "closed"
            po.closed_by = user_id
            po.closed_at = now
        else:
            po.status = "partial" if any((i.received_qty or 0) > 0 for i in po.items) else "approved"
            note = (reason or "").strip()
            po.close_reason = f"Close rejected{': ' + note if note else ''}"
            po.close_requested_by = po.close_requested_at = None
        po.updated_at = now
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
        # One GRN can receive lines from several POs of the same vendor.
        received_po_ids = {body.purchase_order_id} if body.purchase_order_id else set()

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

            # Excess Delivery (§6): the portion of this GRN's accepted_qty
            # that pushes the PO item's cumulative received_qty past its
            # ordered_qty - computed as a delta so a second over-delivery
            # against an already-exceeded PO item doesn't double-count.
            excess_qty = None
            if item_data.po_item_id:
                po_item_result = await self.db.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.id == item_data.po_item_id)
                )
                po_item = po_item_result.scalar_one_or_none()
                if po_item:
                    old_cumulative = po_item.received_qty
                    new_cumulative = old_cumulative + item_data.accepted_qty
                    excess_qty = max(Decimal("0"), new_cumulative - po_item.ordered_qty) - max(Decimal("0"), old_cumulative - po_item.ordered_qty)
                    po_item.received_qty = new_cumulative
                    received_po_ids.add(po_item.purchase_order_id)

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
                excess_qty=excess_qty,
            )
            self.db.add(entry_item)
            total_taxable += item_total
            total_amount += item_total

        entry.taxable_amount = total_taxable
        entry.total_amount = total_amount
        await self.db.flush()

        # Update PO status if applicable
        if received_po_ids:
            po_result = await self.db.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id.in_(received_po_ids))
                .options(selectinload(PurchaseOrder.items))
            )
            for po in po_result.scalars().all():
                if po.status in ("approved", "partial"):
                    self._apply_receipt_status(po, user_id, now)

        await self.db.flush()

        result = await self.db.execute(
            select(PurchaseEntry)
            .where(PurchaseEntry.id == entry.id)
            .options(selectinload(PurchaseEntry.vendor), selectinload(PurchaseEntry.items))
        )
        return result.scalar_one()

    async def update_purchase_entry(
        self, entry_id: UUID, body: PurchaseEntryUpdate, company_id: UUID, user_id: UUID,
    ) -> PurchaseEntry | None:
        """Corrects a saved GRN. Accepted = received - rejected; the GRN's own
        stock-in rows, the PO lines' received quantities and the PO status
        follow the change. Stock already used elsewhere can't be taken back,
        so a reduction below what is left in the warehouse is refused.
        """
        entry = (await self.db.execute(
            select(PurchaseEntry)
            .where(PurchaseEntry.id == entry_id, PurchaseEntry.company_id == company_id)
            .options(selectinload(PurchaseEntry.items))
        )).scalar_one_or_none()
        if not entry:
            return None
        if entry.status == "cancelled":
            raise BusinessRulesError("GRN_CANCELLED", "A cancelled GRN can't be edited")

        fields = body.model_fields_set
        if body.entry_date is not None:
            entry.entry_date = body.entry_date
        if "invoice_number" in fields:
            entry.invoice_number = body.invoice_number or None
        if "invoice_date" in fields:
            entry.invoice_date = body.invoice_date
        if "notes" in fields:
            entry.notes = body.notes or None

        items_by_id = {it.id: it for it in entry.items}
        touched_po_ids: set[UUID] = set()
        for upd in body.items:
            item = items_by_id.get(upd.id)
            if item is None:
                raise BusinessRulesError("GRN_ITEM_NOT_FOUND", "That line isn't on this GRN")
            if upd.received_qty < 0 or upd.rejected_qty < 0 or upd.unit_price < 0:
                raise BusinessRulesError("INVALID_QTY", "Quantities and price can't be negative")
            if upd.rejected_qty > upd.received_qty:
                raise BusinessRulesError("INVALID_QTY", "Rejected can't be more than received")

            new_accepted = upd.received_qty - upd.rejected_qty
            delta = new_accepted - item.accepted_qty
            if delta < 0:
                in_stock = await self.inv.get_balance(company_id, item.product_id, entry.warehouse_id, item.variant_id)
                if in_stock + delta < 0:
                    raise BusinessRulesError(
                        "STOCK_ALREADY_USED",
                        f"Only {in_stock.normalize()} of this item is left in the warehouse, so accepted can't drop by "
                        f"{(-delta).normalize()}. The rest has already been issued or sold.",
                    )

            txn = None
            if item.inv_transaction_id:
                txn = (await self.db.execute(
                    select(InventoryTransaction).where(InventoryTransaction.id == item.inv_transaction_id)
                )).scalar_one_or_none()
            if new_accepted > 0 and txn is not None:
                txn.quantity = new_accepted
                txn.unit_cost = upd.unit_price
                txn.total_cost = new_accepted * upd.unit_price
                txn.transaction_date = entry.entry_date
            elif new_accepted > 0:
                txn = await self.inv.receive(
                    ReceiveParams(
                        company_id=company_id, product_id=item.product_id, variant_id=item.variant_id,
                        warehouse_id=entry.warehouse_id, quantity=new_accepted, unit_id=item.unit_id,
                        unit_cost=upd.unit_price, material_type="raw_material",
                        transaction_date=entry.entry_date, reference_type="purchase_entry",
                        reference_id=entry.id, notes=f"GRN {entry.entry_number}",
                    ),
                    user_id=user_id,
                )
                item.inv_transaction_id = txn.id
            elif txn is not None:
                item.inv_transaction_id = None
                await self.db.flush()
                await self.db.delete(txn)

            if item.po_item_id and delta != 0:
                po_item = (await self.db.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.id == item.po_item_id)
                )).scalar_one_or_none()
                if po_item:
                    before_this_grn = po_item.received_qty - item.accepted_qty
                    po_item.received_qty = before_this_grn + new_accepted
                    item.excess_qty = (
                        max(Decimal("0"), po_item.received_qty - po_item.ordered_qty)
                        - max(Decimal("0"), before_this_grn - po_item.ordered_qty)
                    )
                    touched_po_ids.add(po_item.purchase_order_id)

            item.received_qty = upd.received_qty
            item.rejected_qty = upd.rejected_qty
            item.accepted_qty = new_accepted
            item.unit_price = upd.unit_price
            item.total_amount = (new_accepted * upd.unit_price).quantize(Decimal("0.01"))
            item.quality_status = (
                "accepted" if upd.rejected_qty == 0 else ("rejected" if new_accepted == 0 else "partial")
            )

        # Stock-in dates follow the GRN date even for lines not edited.
        if body.entry_date is not None:
            for item in entry.items:
                if item.inv_transaction_id:
                    await self.db.execute(
                        InventoryTransaction.__table__.update()
                        .where(InventoryTransaction.id == item.inv_transaction_id)
                        .values(transaction_date=entry.entry_date)
                    )

        entry.taxable_amount = sum((it.total_amount for it in entry.items), Decimal("0"))
        entry.total_amount = entry.taxable_amount
        entry.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        if touched_po_ids:
            pos = (await self.db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id.in_(touched_po_ids)).options(selectinload(PurchaseOrder.items))
            )).scalars().all()
            for po in pos:
                if po.status not in ("approved", "partial", "received", "close_requested"):
                    continue
                self._apply_receipt_status(po, user_id, entry.updated_at)
            await self.db.flush()

        return await self.get_purchase_entry(entry.id, company_id)

    async def last_rate(self, company_id: UUID, product_id: UUID, vendor_id: UUID | None) -> dict | None:
        """The rate to suggest for a product: its latest PO or GRN rate from
        this vendor, else from any vendor, else the product's cost price."""
        from app.models.master import Product

        async def latest(for_vendor: UUID | None) -> dict | None:
            po_q = (
                select(PurchaseOrderItem.unit_price, PurchaseOrder.order_date.label("dated"), PurchaseOrder.po_number.label("ref"))
                .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
                .where(PurchaseOrder.company_id == company_id, PurchaseOrderItem.product_id == product_id,
                       PurchaseOrder.status != "cancelled", PurchaseOrder.deleted_at.is_(None))
            )
            grn_q = (
                select(PurchaseEntryItem.unit_price, PurchaseEntry.entry_date.label("dated"), PurchaseEntry.entry_number.label("ref"))
                .join(PurchaseEntry, PurchaseEntry.id == PurchaseEntryItem.purchase_entry_id)
                .where(PurchaseEntry.company_id == company_id, PurchaseEntryItem.product_id == product_id,
                       PurchaseEntry.status != "cancelled")
            )
            if for_vendor:
                po_q = po_q.where(PurchaseOrder.vendor_id == for_vendor)
                grn_q = grn_q.where(PurchaseEntry.vendor_id == for_vendor)
            po_q = po_q.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.created_at.desc())
            grn_q = grn_q.order_by(PurchaseEntry.entry_date.desc(), PurchaseEntry.created_at.desc())
            rows = [r for q in (po_q, grn_q) for r in (await self.db.execute(q.limit(1))).all()]
            if not rows:
                return None
            best = max(rows, key=lambda r: r.dated)
            return {"unit_price": best.unit_price, "source": best.ref, "date": best.dated, "same_vendor": for_vendor is not None}

        found = (await latest(vendor_id) if vendor_id else None) or await latest(None)
        if found:
            return found
        cost = (await self.db.execute(
            select(Product.cost_price).where(Product.id == product_id, Product.company_id == company_id)
        )).scalar_one_or_none()
        if cost is not None:
            return {"unit_price": cost, "source": "product cost price", "date": None, "same_vendor": False}
        return None
