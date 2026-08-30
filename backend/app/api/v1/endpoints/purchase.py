"""Purchase module endpoints: vendors, purchase orders, GRNs."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.models.purchase import PurchaseOrder, PurchaseEntry, Vendor
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.purchase import (
    PurchaseEntryCreate, PurchaseEntryOut,
    PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderUpdate,
    VendorCreate, VendorOut, VendorUpdate,
    GRNItemOut, POItemOut,
)
from app.services.purchase import PurchaseService

router = APIRouter(prefix="/purchase", tags=["purchase"])


def _vendor_out(v: Vendor) -> VendorOut:
    return VendorOut.model_validate(v)


def _po_out(po: PurchaseOrder) -> PurchaseOrderOut:
    return PurchaseOrderOut(
        id=po.id,
        po_number=po.po_number,
        vendor_id=po.vendor_id,
        vendor_name=po.vendor.name if po.vendor else None,
        warehouse_id=po.warehouse_id,
        order_date=po.order_date,
        expected_date=po.expected_date,
        status=po.status,
        taxable_amount=po.taxable_amount,
        cgst_amount=po.cgst_amount,
        sgst_amount=po.sgst_amount,
        igst_amount=po.igst_amount,
        total_amount=po.total_amount,
        notes=po.notes,
        terms=po.terms,
        approved_by=po.approved_by,
        approved_at=po.approved_at,
        items=[POItemOut.model_validate(i) for i in po.items],
    )


def _entry_out(e: PurchaseEntry) -> PurchaseEntryOut:
    return PurchaseEntryOut(
        id=e.id,
        entry_number=e.entry_number,
        purchase_order_id=e.purchase_order_id,
        vendor_id=e.vendor_id,
        vendor_name=e.vendor.name if e.vendor else None,
        warehouse_id=e.warehouse_id,
        entry_date=e.entry_date,
        invoice_number=e.invoice_number,
        invoice_date=e.invoice_date,
        status=e.status,
        taxable_amount=e.taxable_amount,
        total_amount=e.total_amount,
        notes=e.notes,
        items=[GRNItemOut.model_validate(i) for i in e.items],
    )


# ── Vendors ─────────────────────────────────────────────────────────────────

@router.get("/vendors")
async def list_vendors(
    db: DBSession,
    user: AuthUser,
    active_only: bool = True,
    vendor_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("purchase.view")
    svc = PurchaseService(db)
    vendors, total = await svc.list_vendors(
        user.company_id, active_only=active_only, vendor_type=vendor_type,
        search=search, page=page, page_size=page_size,
    )
    return ApiResponse(
        success=True,
        data=[_vendor_out(v) for v in vendors],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/vendors", status_code=201)
async def create_vendor(body: VendorCreate, db: DBSession, user: AuthUser):
    user.require("purchase.create")
    svc = PurchaseService(db)

    existing = await db.execute(
        select(Vendor).where(Vendor.company_id == user.company_id, Vendor.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Vendor code '{body.code}' already exists")

    vendor = await svc.create_vendor(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_vendor_out(vendor))


@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.view")
    svc = PurchaseService(db)
    vendor = await svc.get_vendor(vendor_id, user.company_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return ApiResponse(success=True, data=_vendor_out(vendor))


@router.patch("/vendors/{vendor_id}")
async def update_vendor(vendor_id: UUID, body: VendorUpdate, db: DBSession, user: AuthUser):
    user.require("purchase.edit")
    svc = PurchaseService(db)
    vendor = await svc.update_vendor(vendor_id, body, user.company_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return ApiResponse(success=True, data=_vendor_out(vendor))


# ── Purchase Orders ──────────────────────────────────────────────────────────

@router.get("/orders")
async def list_purchase_orders(
    db: DBSession,
    user: AuthUser,
    status: str | None = None,
    vendor_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("purchase.view")
    svc = PurchaseService(db)
    orders, total = await svc.list_purchase_orders(
        user.company_id, status=status, vendor_id=vendor_id, page=page, page_size=page_size,
    )
    return ApiResponse(
        success=True,
        data=[_po_out(po) for po in orders],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/orders", status_code=201)
async def create_purchase_order(body: PurchaseOrderCreate, db: DBSession, user: AuthUser):
    user.require("purchase.create")
    if not body.items:
        raise HTTPException(400, "Purchase order must have at least one item")
    svc = PurchaseService(db)
    po = await svc.create_purchase_order(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_po_out(po))


@router.get("/orders/{po_id}")
async def get_purchase_order(po_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.view")
    svc = PurchaseService(db)
    po = await svc.get_purchase_order(po_id, user.company_id)
    if not po:
        raise HTTPException(404, "Purchase order not found")
    return ApiResponse(success=True, data=_po_out(po))


@router.patch("/orders/{po_id}")
async def update_purchase_order(po_id: UUID, body: PurchaseOrderUpdate, db: DBSession, user: AuthUser):
    user.require("purchase.edit")
    svc = PurchaseService(db)
    po = await svc.update_purchase_order(po_id, body, user.company_id)
    if not po:
        raise HTTPException(400, "Purchase order not found or not in draft status")
    return ApiResponse(success=True, data=_po_out(po))


@router.post("/orders/{po_id}/approve")
async def approve_purchase_order(po_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.approve")
    svc = PurchaseService(db)
    po = await svc.approve_purchase_order(po_id, user.company_id, user.user_id)
    if not po:
        raise HTTPException(400, "Purchase order not found or not in draft status")
    return ApiResponse(success=True, data=_po_out(po))


@router.post("/orders/{po_id}/cancel")
async def cancel_purchase_order(po_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.edit")
    svc = PurchaseService(db)
    po = await svc.cancel_purchase_order(po_id, user.company_id)
    if not po:
        raise HTTPException(400, "Purchase order cannot be cancelled in its current status")
    return ApiResponse(success=True, data=_po_out(po))


# ── Purchase Entries (GRN) ───────────────────────────────────────────────────

@router.get("/entries")
async def list_purchase_entries(
    db: DBSession,
    user: AuthUser,
    status: str | None = None,
    vendor_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("purchase.view")
    svc = PurchaseService(db)
    entries, total = await svc.list_purchase_entries(
        user.company_id, status=status, vendor_id=vendor_id, page=page, page_size=page_size,
    )
    return ApiResponse(
        success=True,
        data=[_entry_out(e) for e in entries],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/entries", status_code=201)
async def create_purchase_entry(body: PurchaseEntryCreate, db: DBSession, user: AuthUser):
    user.require("purchase.create")
    if not body.items:
        raise HTTPException(400, "Purchase entry must have at least one item")
    svc = PurchaseService(db)
    entry = await svc.create_purchase_entry(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_entry_out(entry))


@router.get("/entries/{entry_id}")
async def get_purchase_entry(entry_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.view")
    svc = PurchaseService(db)
    entry = await svc.get_purchase_entry(entry_id, user.company_id)
    if not entry:
        raise HTTPException(404, "Purchase entry not found")
    return ApiResponse(success=True, data=_entry_out(entry))
