"""Sales module endpoints: customers, quotations, sales orders, deliveries, invoices."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.models.sales import Customer, Delivery, Invoice, NatureOfBusiness, Quotation, SalesOrder
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.sales import (
    CustomerCreate, CustomerListOut, CustomerOut, CustomerUpdate,
    DeliveryCreate, DeliveryItemOut, DeliveryOut,
    InvoiceCreate, InvoiceOut,
    NatureOfBusinessOut,
    QuotationCreate, QuotationItemOut, QuotationOut, QuotationUpdate,
    SalesOrderCreate, SalesOrderOut, SalesOrderUpdate, SOItemOut,
)
from app.services.sales import SalesService

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
        items=[SOItemOut.model_validate(i) for i in so.items],
    )


def _delivery_out(d: Delivery) -> DeliveryOut:
    return DeliveryOut(
        id=d.id, delivery_number=d.delivery_number, sales_order_id=d.sales_order_id,
        customer_id=d.customer_id,
        customer_name=d.customer.legal_name if d.customer else None,
        warehouse_id=d.warehouse_id, delivery_date=d.delivery_date, status=d.status,
        transporter=d.transporter, lr_number=d.lr_number, vehicle_number=d.vehicle_number,
        notes=d.notes, dispatched_at=d.dispatched_at,
        items=[DeliveryItemOut.model_validate(i) for i in d.items],
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
    so = await svc.create_sales_order(body, user.company_id, user.user_id)
    return ApiResponse(success=True, data=_so_out(so))


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
    return ApiResponse(success=True, data=_delivery_out(d))


@router.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    svc = SalesService(db)
    d = await svc.get_delivery(delivery_id, user.company_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    return ApiResponse(success=True, data=_delivery_out(d))


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
