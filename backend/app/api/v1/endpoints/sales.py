"""Sales module endpoints: customers, quotations, sales orders, deliveries, invoices."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import AuthUser, DBSession
from app.domain.business_rules import BusinessRulesError
from app.models.company import Company
from app.models.master import Product, ProductVariant, Unit
from app.models.sales import Customer, Delivery, Invoice, NatureOfBusiness, PriceHistory, PriceList, PriceListItem, Quotation, SalesOrder, SalesReturn
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.sales import (
    CustomerCreate, CustomerListOut, CustomerOut, CustomerUpdate,
    DeliveryCreate, DeliveryItemOut, DeliveryOut,
    InvoiceCreate, InvoiceOut,
    NatureOfBusinessOut,
    PriceHistoryOut, PriceListCreate, PriceListItemCreate, PriceListItemOut,
    PriceListItemUpdate, PriceListOut, PriceListUpdate, PriceResolveOut,
    QuotationCreate, QuotationItemOut, QuotationOut, QuotationUpdate,
    SalesOrderCreate, SalesOrderOut, SalesOrderUpdate, SOItemOut, StockCheckOut,
    SalesReturnCreate, SalesReturnOut, SalesReturnItemOut,
)
from app.services.inventory import InventoryService
from app.services.packing_slip import packing_slip_filename, render_packing_slip_pdf
from app.services.pricing import PricingService
from app.services.sales import SalesService, QuantityValidationError


def _now() -> datetime:
    return datetime.now(timezone.utc)

router = APIRouter(prefix="/sales", tags=["sales"])


def _customer_out(c: Customer) -> CustomerOut:
    return CustomerOut.model_validate(c)


def _quotation_out(q: Quotation) -> QuotationOut:
    return QuotationOut(
        id=q.id, quotation_number=q.quotation_number,
        customer_id=q.customer_id,
        customer_name=q.customer.legal_name if q.customer else None,
        quotation_date=q.quotation_date, valid_until=q.valid_until, status=q.status,
        subtotal=q.subtotal, discount_amount=q.discount_amount, taxable_amount=q.taxable_amount,
        cgst_amount=q.cgst_amount, sgst_amount=q.sgst_amount, igst_amount=q.igst_amount,
        total_amount=q.total_amount, notes=q.notes, terms=q.terms,
        approved_by=q.approved_by, approved_at=q.approved_at,
        converted_order_id=q.converted_order_id,
        items=[QuotationItemOut.model_validate(i) for i in q.items],
    )


def _so_out(so: SalesOrder) -> SalesOrderOut:
    return SalesOrderOut(
        id=so.id, order_number=so.order_number,
        customer_id=so.customer_id,
        customer_name=so.customer.legal_name if so.customer else None,
        quotation_id=so.quotation_id, order_date=so.order_date,
        expected_delivery=so.expected_delivery, status=so.status,
        subtotal=so.subtotal, discount_amount=so.discount_amount, taxable_amount=so.taxable_amount,
        cgst_amount=so.cgst_amount, sgst_amount=so.sgst_amount, igst_amount=so.igst_amount,
        total_amount=so.total_amount, notes=so.notes,
        customer_po_number=so.customer_po_number, customer_po_quantity=so.customer_po_quantity,
        po_tolerance_pct=so.po_tolerance_pct,
        items=[SOItemOut.model_validate(i) for i in so.items],
    )


def _delivery_out(d: Delivery) -> DeliveryOut:
    return DeliveryOut(
        id=d.id, delivery_number=d.delivery_number, sales_order_id=d.sales_order_id,
        customer_id=d.customer_id,
        customer_name=d.customer.legal_name if d.customer else None,
        warehouse_id=d.warehouse_id, delivery_date=d.delivery_date, status=d.status,
        purpose=d.purpose,
        transporter=d.transporter, lr_number=d.lr_number, vehicle_number=d.vehicle_number,
        notes=d.notes, dispatched_at=d.dispatched_at,
        carton_count=d.carton_count, package_count=d.package_count, packing_marks=d.packing_marks,
        gross_weight=d.gross_weight, net_weight=d.net_weight,
        items=[DeliveryItemOut.model_validate(i) for i in d.items],
    )


async def _enrich_delivery_out(db: DBSession, d: Delivery, out: DeliveryOut) -> DeliveryOut:
    """Resolves per-item product/variant/lot names and cumulative returned
    qty, plus linked Sales Return records - the detail-view-only lookups
    `_delivery_out` itself skips to keep the list endpoint light."""
    item_ids = [i.id for i in d.items]
    product_ids = {i.product_id for i in d.items}
    variant_ids = {i.variant_id for i in d.items if i.variant_id}
    lot_ids = {i.lot_id for i in d.items if i.lot_id}

    product_names: dict[UUID, str] = {}
    if product_ids:
        rows = (await db.execute(select(Product.id, Product.name).where(Product.id.in_(product_ids)))).all()
        product_names = {pid: name for pid, name in rows}

    variant_info: dict[UUID, tuple[str | None, str | None, str | None]] = {}
    if variant_ids:
        from app.models.master import Colour, Size
        rows = (await db.execute(
            select(ProductVariant.id, ProductVariant.sku, Size.name, Colour.name)
            .outerjoin(Size, Size.id == ProductVariant.size_id)
            .outerjoin(Colour, Colour.id == ProductVariant.colour_id)
            .where(ProductVariant.id.in_(variant_ids))
        )).all()
        variant_info = {vid: (sku, size_name, colour_name) for vid, sku, size_name, colour_name in rows}

    lot_numbers: dict[UUID, str] = {}
    if lot_ids:
        from app.models.inventory import InventoryLot
        rows = (await db.execute(select(InventoryLot.id, InventoryLot.lot_number).where(InventoryLot.id.in_(lot_ids)))).all()
        lot_numbers = {lid: num for lid, num in rows}

    returned_by_item: dict[UUID, Decimal] = {}
    if item_ids:
        from app.models.sales import SalesReturnItem
        rows = (await db.execute(
            select(SalesReturnItem.delivery_item_id, func.sum(SalesReturnItem.quantity))
            .where(SalesReturnItem.delivery_item_id.in_(item_ids))
            .group_by(SalesReturnItem.delivery_item_id)
        )).all()
        returned_by_item = {did: qty for did, qty in rows}

    for item_out in out.items:
        item_out.product_name = product_names.get(item_out.product_id)
        if item_out.variant_id and item_out.variant_id in variant_info:
            sku, size_name, colour_name = variant_info[item_out.variant_id]
            item_out.sku = sku
            item_out.size_name = size_name
            item_out.colour_name = colour_name
        if item_out.lot_id:
            item_out.lot_number = lot_numbers.get(item_out.lot_id)
        item_out.returned_qty = returned_by_item.get(item_out.id, Decimal("0"))

    svc = SalesService(db)
    returns = await svc.list_sales_returns_for_delivery(d.id, d.company_id)
    out.returns = [_sales_return_out(r) for r in returns]
    return out


def _sales_return_out(r: SalesReturn) -> SalesReturnOut:
    return SalesReturnOut(
        id=r.id, return_number=r.return_number, delivery_id=r.delivery_id,
        customer_id=r.customer_id,
        customer_name=r.customer.legal_name if r.customer else None,
        return_date=r.return_date, reason=r.reason, status=r.status, notes=r.notes,
        items=[SalesReturnItemOut.model_validate(i) for i in r.items],
    )


def _invoice_out(inv: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=inv.id, invoice_number=inv.invoice_number, customer_id=inv.customer_id,
        customer_name=inv.customer.legal_name if inv.customer else None,
        sales_order_id=inv.sales_order_id, delivery_id=inv.delivery_id,
        invoice_date=inv.invoice_date, due_date=inv.due_date, status=inv.status,
        subtotal=inv.subtotal, taxable_amount=inv.taxable_amount,
        cgst_amount=inv.cgst_amount, sgst_amount=inv.sgst_amount, igst_amount=inv.igst_amount,
        total_amount=inv.total_amount, paid_amount=inv.paid_amount,
        balance_amount=inv.balance_amount, notes=inv.notes,
    )


# ── Nature of Business ───────────────────────────────────────────────────────

@router.get("/nature-of-business")
async def list_nature_of_business(db: DBSession, user: AuthUser):
    user.require("sales.view")
    result = await db.execute(
        select(NatureOfBusiness)
        .where(NatureOfBusiness.is_active.is_(True))
        .order_by(NatureOfBusiness.sort_order)
    )
    items = result.scalars().all()
    return ApiResponse(success=True, data=[NatureOfBusinessOut.model_validate(i) for i in items])


# ── Customers ────────────────────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(
    db: DBSession, user: AuthUser,
    active_only: bool = True, search: str | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    customers, total = await svc.list_customers(
        user.company_id, active_only=active_only, search=search, page=page, page_size=page_size,
    )
    return ApiResponse(
        success=True,
        data=[CustomerListOut.model_validate(c) for c in customers],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/customers", status_code=201)
async def create_customer(body: CustomerCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    existing = await db.execute(
        select(Customer).where(Customer.company_id == user.company_id, Customer.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Customer code '{body.code}' already exists")
    svc = SalesService(db)
    c = await svc.create_customer(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_customer_out(c))


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    c = await svc.get_customer(customer_id, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return ApiResponse(success=True, data=_customer_out(c))


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: UUID, body: CustomerUpdate, db: DBSession, user: AuthUser):
    user.require("sales.edit")
    svc = SalesService(db)
    c = await svc.update_customer(customer_id, body, user.company_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return ApiResponse(success=True, data=_customer_out(c))


# ── Quotations ────────────────────────────────────────────────────────────────

@router.get("/quotations")
async def list_quotations(
    db: DBSession, user: AuthUser,
    status: str | None = None, customer_id: UUID | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    quotations, total = await svc.list_quotations(
        user.company_id, status=status, customer_id=customer_id, page=page, page_size=page_size,
    )
    return ApiResponse(success=True, data=[_quotation_out(q) for q in quotations],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/quotations", status_code=201)
async def create_quotation(body: QuotationCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    if not body.items:
        raise HTTPException(400, "Quotation must have at least one item")
    svc = SalesService(db)
    q = await svc.create_quotation(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_quotation_out(q))


@router.get("/quotations/{quotation_id}")
async def get_quotation(quotation_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    q = await svc.get_quotation(quotation_id, user.company_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    return ApiResponse(success=True, data=_quotation_out(q))


@router.patch("/quotations/{quotation_id}")
async def update_quotation(quotation_id: UUID, body: QuotationUpdate, db: DBSession, user: AuthUser):
    user.require("sales.edit")
    svc = SalesService(db)
    q = await svc.update_quotation(quotation_id, body, user.company_id)
    if not q:
        raise HTTPException(400, "Quotation not found or not editable")
    return ApiResponse(success=True, data=_quotation_out(q))


@router.post("/quotations/{quotation_id}/send")
async def send_quotation(quotation_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.edit")
    svc = SalesService(db)
    q = await svc.send_quotation(quotation_id, user.company_id)
    if not q:
        raise HTTPException(400, "Quotation not found or already sent")
    return ApiResponse(success=True, data=_quotation_out(q))


@router.post("/quotations/{quotation_id}/approve")
async def approve_quotation(quotation_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.approve")
    svc = SalesService(db)
    q = await svc.approve_quotation(quotation_id, user.company_id, user.user_id)
    if not q:
        raise HTTPException(400, "Quotation not found or not approvable")
    return ApiResponse(success=True, data=_quotation_out(q))


class ConvertBody(QuotationUpdate):
    from datetime import date as _date
    order_date: _date
    expected_delivery: _date | None = None
    intrastate: bool = True


@router.post("/quotations/{quotation_id}/convert")
async def convert_quotation(quotation_id: UUID, body: ConvertBody, db: DBSession, user: AuthUser):
    user.require("sales.create")
    svc = SalesService(db)
    so = await svc.convert_quotation_to_so(
        quotation_id, user.company_id, user.user_id,
        body.order_date, body.expected_delivery, body.intrastate,
    )
    if not so:
        raise HTTPException(400, "Quotation not found or not convertible")
    return ApiResponse(success=True, data=_so_out(so))


# ── Sales Orders ──────────────────────────────────────────────────────────────

@router.get("/orders")
async def list_sales_orders(
    db: DBSession, user: AuthUser,
    status: str | None = None, customer_id: UUID | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    orders, total = await svc.list_sales_orders(
        user.company_id, status=status, customer_id=customer_id, page=page, page_size=page_size,
    )
    return ApiResponse(success=True, data=[_so_out(so) for so in orders],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/orders", status_code=201)
async def create_sales_order(body: SalesOrderCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    if not body.items:
        raise HTTPException(400, "Sales order must have at least one item")
    svc = SalesService(db)
    try:
        so = await svc.create_sales_order(body, user.company_id, user.user_id)
    except BusinessRulesError as e:
        raise HTTPException(422, str(e))
    return ApiResponse(success=True, data=_so_out(so))


@router.get("/orders/stock-check")
async def check_order_stock(
    db: DBSession, user: AuthUser,
    product_id: UUID, quantity: Decimal, variant_id: UUID | None = None,
):
    """Informational only (ERP Upgrade §2) - never blocks order creation.
    Lets the Sales Order form show Ordered/Available/Committed/Remaining
    before the user confirms, without forcing the order to fit. Must stay
    registered before GET /orders/{so_id} - otherwise FastAPI tries to
    parse "stock-check" as a so_id UUID and 422s before this ever matches."""
    user.require("sales.view")
    sales_svc = SalesService(db)
    inv_svc = InventoryService(db)
    available = await inv_svc.get_total_balance(user.company_id, product_id, variant_id)
    committed = await sales_svc.get_committed_quantity(user.company_id, product_id, variant_id)
    remaining = available - committed
    return ApiResponse(success=True, data=StockCheckOut(
        ordered_quantity=quantity,
        available_stock=available,
        committed_quantity=committed,
        remaining_quantity=remaining,
        can_fulfill=remaining >= quantity,
    ))


@router.get("/orders/{so_id}")
async def get_sales_order(so_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    so = await svc.get_sales_order(so_id, user.company_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    return ApiResponse(success=True, data=_so_out(so))


@router.post("/orders/{so_id}/cancel")
async def cancel_sales_order(so_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.edit")
    svc = SalesService(db)
    so = await svc.cancel_sales_order(so_id, user.company_id)
    if not so:
        raise HTTPException(400, "Sales order cannot be cancelled in its current status")
    return ApiResponse(success=True, data=_so_out(so))


# ── Deliveries ────────────────────────────────────────────────────────────────

@router.get("/deliveries")
async def list_deliveries(
    db: DBSession, user: AuthUser,
    status: str | None = None, sales_order_id: UUID | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    deliveries, total = await svc.list_deliveries(
        user.company_id, status=status, sales_order_id=sales_order_id, page=page, page_size=page_size,
    )
    return ApiResponse(success=True, data=[_delivery_out(d) for d in deliveries],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/deliveries", status_code=201)
async def create_delivery(body: DeliveryCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    if not body.items:
        raise HTTPException(400, "Delivery must have at least one item")
    svc = SalesService(db)
    try:
        d = await svc.create_delivery(body, user.company_id, user.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # BusinessRulesError (insufficient stock) is left to the global handler
    # in main.py, which now reports available/shortage alongside the
    # message - never silently issuing less than requested (Phase 10).
    return ApiResponse(success=True, data=_delivery_out(d))


@router.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    d = await svc.get_delivery(delivery_id, user.company_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    out = await _enrich_delivery_out(db, d, _delivery_out(d))
    return ApiResponse(success=True, data=out)


# ── Sales Returns ─────────────────────────────────────────────────────────────

@router.get("/returns")
async def list_sales_returns(
    db: DBSession, user: AuthUser,
    customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    returns, total = await svc.list_sales_returns(user.company_id, customer_id=customer_id, page=page, page_size=page_size)
    return ApiResponse(success=True, data=[_sales_return_out(r) for r in returns],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/returns", status_code=201)
async def create_sales_return(body: SalesReturnCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    if not body.items:
        raise HTTPException(400, "A return must have at least one item")
    svc = SalesService(db)
    try:
        r = await svc.create_sales_return(body, user.company_id, user.user_id)
    except QuantityValidationError as e:
        raise HTTPException(422, str(e))
    return ApiResponse(success=True, data=_sales_return_out(r))


@router.get("/returns/{return_id}")
async def get_sales_return(return_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    r = await svc.get_sales_return(return_id, user.company_id)
    if not r:
        raise HTTPException(404, "Sales return not found")
    return ApiResponse(success=True, data=_sales_return_out(r))


@router.get("/deliveries/{delivery_id}/packing-slip")
async def get_packing_slip(delivery_id: UUID, db: DBSession, user: AuthUser):
    """Printable Packing Slip (ERP Upgrade §4), generated server-side from
    the existing Delivery record - no second source of truth, no new
    fields required from the caller."""
    user.require("sales.view")
    svc = SalesService(db)
    d = await svc.get_delivery(delivery_id, user.company_id)
    if not d:
        raise HTTPException(404, "Delivery not found")

    company = (await db.execute(select(Company).where(Company.id == user.company_id))).scalar_one_or_none()

    product_ids = {i.product_id for i in d.items}
    variant_ids = {i.variant_id for i in d.items if i.variant_id}
    unit_ids = {i.unit_id for i in d.items}

    products = {}
    if product_ids:
        rows = await db.execute(
            select(Product).where(Product.id.in_(product_ids)).options(selectinload(Product.hsn))
        )
        products = {p.id: p for p in rows.scalars()}

    variants = {}
    if variant_ids:
        rows = await db.execute(select(ProductVariant).where(ProductVariant.id.in_(variant_ids)))
        variants = {v.id: v for v in rows.scalars()}

    units = {}
    if unit_ids:
        rows = await db.execute(select(Unit).where(Unit.id.in_(unit_ids)))
        units = {u.id: u for u in rows.scalars()}

    item_rows = []
    for i in d.items:
        product = products.get(i.product_id)
        variant = variants.get(i.variant_id) if i.variant_id else None
        unit = units.get(i.unit_id)
        item_rows.append({
            "product_name": product.name if product else None,
            "sku_or_hsn": (variant.sku if variant else None) or (product.hsn.hsn if product and product.hsn else None),
            "quantity": str(i.quantity),
            "unit": unit.abbreviation if unit else None,
        })

    customer_dict = None
    if d.customer:
        default_addr = next((a for a in d.customer.addresses if a.is_default), d.customer.addresses[0] if d.customer.addresses else None)
        address_str = None
        if default_addr:
            parts = [default_addr.line1, default_addr.line2, default_addr.city, default_addr.state, default_addr.pincode]
            address_str = ", ".join(p for p in parts if p)
        customer_dict = {
            "name": d.customer.legal_name,
            "address": address_str,
            "gstin": d.customer.gstin,
            "phone": d.customer.mobile,
        }

    sales_order_dict = None
    if d.sales_order:
        sales_order_dict = {"order_number": d.sales_order.order_number, "order_date": str(d.sales_order.order_date)}

    delivery_dict = {
        "delivery_number": d.delivery_number,
        "delivery_date": str(d.delivery_date),
        "carton_count": d.carton_count,
        "package_count": d.package_count,
        "packing_marks": d.packing_marks,
        "gross_weight": str(d.gross_weight) if d.gross_weight is not None else None,
        "net_weight": str(d.net_weight) if d.net_weight is not None else None,
        "transporter": d.transporter,
        "lr_number": d.lr_number,
        "vehicle_number": d.vehicle_number,
        "dispatched_at": d.dispatched_at.strftime("%d %b %Y, %H:%M") if d.dispatched_at else None,
    }

    pdf_bytes = render_packing_slip_pdf(
        company_name=company.name if company else None,
        delivery=delivery_dict,
        sales_order=sales_order_dict,
        customer=customer_dict,
        items=item_rows,
    )
    filename = packing_slip_filename(d.delivery_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices")
async def list_invoices(
    db: DBSession, user: AuthUser,
    status: str | None = None, customer_id: UUID | None = None,
    page: int = 1, page_size: int = 50,
):
    user.require("sales.view")
    svc = SalesService(db)
    invoices, total = await svc.list_invoices(
        user.company_id, status=status, customer_id=customer_id, page=page, page_size=page_size,
    )
    return ApiResponse(success=True, data=[_invoice_out(i) for i in invoices],
                       meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/invoices", status_code=201)
async def create_invoice(body: InvoiceCreate, db: DBSession, user: AuthUser):
    user.require("sales.create")
    svc = SalesService(db)
    inv = await svc.create_invoice_from_delivery(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_invoice_out(inv))


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    inv = await svc.get_invoice(invoice_id, user.company_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return ApiResponse(success=True, data=_invoice_out(inv))


# ── Price Lists (Phase 7) ──────────────────────────────────────────────────────
# Catalogue/customer-specific pricing — items always reference the real ERP
# Product/ProductVariant master, never a separate CRM-only product table.

@router.get("/price-lists")
async def list_price_lists(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(PriceList, func.count(PriceListItem.id))
        .outerjoin(PriceListItem, PriceListItem.price_list_id == PriceList.id)
        .where(PriceList.company_id == user.company_id)
        .group_by(PriceList.id)
        .order_by(PriceList.name)
    )
    return ApiResponse(success=True, data=[
        PriceListOut(id=pl.id, name=pl.name, is_default=pl.is_default,
                      valid_from=pl.valid_from, valid_to=pl.valid_to, item_count=count)
        for pl, count in result.all()
    ])


@router.post("/price-lists", status_code=201)
async def create_price_list(body: PriceListCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Price list name is required")
    pl = PriceList(company_id=user.company_id, name=name, is_default=body.is_default,
                    valid_from=body.valid_from, valid_to=body.valid_to)
    db.add(pl)
    await db.commit()
    await db.refresh(pl)
    return ApiResponse(success=True, data=PriceListOut(
        id=pl.id, name=pl.name, is_default=pl.is_default, valid_from=pl.valid_from, valid_to=pl.valid_to,
    ), message="Price list created")


@router.patch("/price-lists/{price_list_id}")
async def update_price_list(price_list_id: UUID, body: PriceListUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id, PriceList.company_id == user.company_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Price list not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(pl, field, val)
    await db.commit()
    await db.refresh(pl)
    return ApiResponse(success=True, data=PriceListOut(
        id=pl.id, name=pl.name, is_default=pl.is_default, valid_from=pl.valid_from, valid_to=pl.valid_to,
    ), message="Price list updated")


@router.delete("/price-lists/{price_list_id}")
async def delete_price_list(price_list_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id, PriceList.company_id == user.company_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Price list not found")
    in_use = await db.execute(select(func.count(Customer.id)).where(Customer.price_list_id == price_list_id))
    if (in_use.scalar() or 0) > 0:
        raise HTTPException(409, "Cannot delete — this price list is assigned to existing customers")
    await db.delete(pl)
    await db.commit()
    return ApiResponse(success=True, message="Price list deleted")


async def _price_list_item_out(db, item: PriceListItem) -> PriceListItemOut:
    product = (await db.execute(select(Product.name).where(Product.id == item.product_id))).scalar_one_or_none()
    variant_sku = None
    if item.variant_id:
        variant_sku = (await db.execute(select(ProductVariant.sku).where(ProductVariant.id == item.variant_id))).scalar_one_or_none()
    customer_name = None
    if item.customer_id:
        customer_name = (await db.execute(select(Customer.legal_name).where(Customer.id == item.customer_id))).scalar_one_or_none()
    return PriceListItemOut(
        id=item.id, price_list_id=item.price_list_id, product_id=item.product_id, product_name=product,
        variant_id=item.variant_id, variant_sku=variant_sku, customer_id=item.customer_id, customer_name=customer_name,
        min_quantity=item.min_quantity, max_quantity=item.max_quantity, unit_price=item.unit_price,
        discount_pct=item.discount_pct, valid_from=item.valid_from, valid_to=item.valid_to,
    )


@router.get("/price-lists/{price_list_id}/items")
async def list_price_list_items(price_list_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.view")
    pl_check = await db.execute(select(PriceList.id).where(PriceList.id == price_list_id, PriceList.company_id == user.company_id))
    if not pl_check.scalar_one_or_none():
        raise HTTPException(404, "Price list not found")
    result = await db.execute(select(PriceListItem).where(PriceListItem.price_list_id == price_list_id))
    items = result.scalars().all()
    return ApiResponse(success=True, data=[await _price_list_item_out(db, i) for i in items])


@router.post("/price-lists/{price_list_id}/items", status_code=201)
async def create_price_list_item(price_list_id: UUID, body: PriceListItemCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    pl_check = await db.execute(select(PriceList.id).where(PriceList.id == price_list_id, PriceList.company_id == user.company_id))
    if not pl_check.scalar_one_or_none():
        raise HTTPException(404, "Price list not found")
    item = PriceListItem(
        price_list_id=price_list_id, product_id=body.product_id, variant_id=body.variant_id,
        customer_id=body.customer_id, min_quantity=body.min_quantity, max_quantity=body.max_quantity,
        unit_price=body.unit_price, discount_pct=body.discount_pct,
        valid_from=body.valid_from, valid_to=body.valid_to,
    )
    db.add(item)
    await db.flush()
    db.add(PriceHistory(
        company_id=user.company_id, product_id=item.product_id, variant_id=item.variant_id,
        price_list_item_id=item.id, old_price=None, new_price=item.unit_price,
        changed_by=user.user_id, changed_at=_now(),
    ))
    await db.commit()
    return ApiResponse(success=True, data=await _price_list_item_out(db, item), message="Price added")


@router.patch("/price-lists/items/{item_id}")
async def update_price_list_item(item_id: UUID, body: PriceListItemUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(PriceListItem).join(PriceList, PriceList.id == PriceListItem.price_list_id)
        .where(PriceListItem.id == item_id, PriceList.company_id == user.company_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Price list item not found")
    old_price = item.unit_price
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(item, field, val)
    if item.unit_price != old_price:
        db.add(PriceHistory(
            company_id=user.company_id, product_id=item.product_id, variant_id=item.variant_id,
            price_list_item_id=item.id, old_price=old_price, new_price=item.unit_price,
            changed_by=user.user_id, changed_at=_now(),
        ))
    await db.commit()
    return ApiResponse(success=True, data=await _price_list_item_out(db, item), message="Price updated")


@router.delete("/price-lists/items/{item_id}")
async def delete_price_list_item(item_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(PriceListItem).join(PriceList, PriceList.id == PriceListItem.price_list_id)
        .where(PriceListItem.id == item_id, PriceList.company_id == user.company_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Price list item not found")
    await db.delete(item)
    await db.commit()
    return ApiResponse(success=True, message="Price removed")


@router.get("/price-lists/resolve")
async def resolve_price(
    db: DBSession, user: AuthUser,
    product_id: UUID, variant_id: UUID | None = None, customer_id: UUID | None = None,
    quantity: Decimal = Decimal("1"), on_date: date | None = None,
):
    user.require("master_data.view")
    result = await PricingService(db).get_price(
        company_id=user.company_id, product_id=product_id, variant_id=variant_id,
        customer_id=customer_id, quantity=quantity, on_date=on_date or date.today(),
    )
    return ApiResponse(success=True, data=PriceResolveOut(
        unit_price=result.unit_price, discount_pct=result.discount_pct,
        discount_amount=result.discount_amount, taxable_amount=result.taxable_amount, source=result.source,
    ))


@router.get("/price-history")
async def get_price_history(db: DBSession, user: AuthUser, product_id: UUID, variant_id: UUID | None = None):
    user.require("master_data.view")
    filters = [PriceHistory.company_id == user.company_id, PriceHistory.product_id == product_id]
    if variant_id:
        filters.append(PriceHistory.variant_id == variant_id)
    result = await db.execute(
        select(PriceHistory, User.full_name)
        .outerjoin(User, User.id == PriceHistory.changed_by)
        .where(*filters)
        .order_by(PriceHistory.changed_at.desc())
        .limit(100)
    )
    return ApiResponse(success=True, data=[
        PriceHistoryOut(
            id=h.id, product_id=h.product_id, variant_id=h.variant_id,
            old_price=h.old_price, new_price=h.new_price, changed_by_name=name, changed_at=h.changed_at,
        )
        for h, name in result.all()
    ])
