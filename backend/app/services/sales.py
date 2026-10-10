"""SalesService: customers, quotations, sales orders, deliveries, invoices."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.business_rules import business_rules, BusinessRulesError
from app.models.sales import (
    Customer, CustomerAddress, CustomerContact, CustomerDetail,
    Delivery, DeliveryItem, Invoice,
    Quotation, QuotationItem,
    SalesOrder, SalesOrderItem,
    SalesReturn, SalesReturnItem,
)
from app.schemas.inventory import IssueParams, ReceiveParams
from app.schemas.sales import (
    CustomerCreate, CustomerUpdate,
    DeliveryCreate,
    InvoiceCreate,
    QuotationCreate, QuotationUpdate,
    SalesOrderCreate, SalesOrderUpdate,
    SalesReturnCreate,
)
from app.services.inventory import InventoryService


class QuantityValidationError(ValueError):
    """Raised when a Sales Return would credit more than was ever
    delivered on the referenced DeliveryItem line (Phase 10's "prevent the
    same remainder from being returned or credited twice")."""


def _item_amounts(
    unit_price: Decimal,
    quantity: Decimal,
    discount_pct: Decimal,
    gst_rate: Decimal,
    intrastate: bool,
) -> dict:
    gross = (unit_price * quantity).quantize(Decimal("0.01"))
    discount_amount = (gross * discount_pct / 100).quantize(Decimal("0.01"))
    taxable = (gross - discount_amount).quantize(Decimal("0.01"))
    half = (gst_rate / 2).quantize(Decimal("0.01"))

    if intrastate:
        cgst = (taxable * half / 100).quantize(Decimal("0.01"))
        sgst = cgst
        igst = Decimal("0")
    else:
        cgst = sgst = Decimal("0")
        igst = (taxable * gst_rate / 100).quantize(Decimal("0.01"))

    return {
        "discount_amount": discount_amount,
        "taxable_amount": taxable,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "total_amount": (taxable + cgst + sgst + igst).quantize(Decimal("0.01")),
    }


async def _next_seq(db: AsyncSession, prefix: str, company_id: UUID, model_cls) -> str:
    result = await db.execute(select(func.count()).where(model_cls.company_id == company_id))
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:05d}"


class SalesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    # ── Customers ──────────────────────────────────────────────────────────

    async def list_customers(
        self, company_id: UUID, active_only: bool = True,
        search: str | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Customer], int]:
        q = (
            select(Customer)
            .where(Customer.company_id == company_id, Customer.deleted_at.is_(None))
            .options(selectinload(Customer.addresses), selectinload(Customer.contacts))
        )
        if active_only:
            q = q.where(Customer.is_active.is_(True))
        if search:
            q = q.where(Customer.legal_name.ilike(f"%{search}%") | Customer.code.ilike(f"%{search}%"))

        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(Customer.code).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_customer(self, cid: UUID, company_id: UUID) -> Customer | None:
        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == cid, Customer.company_id == company_id, Customer.deleted_at.is_(None))
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.contacts),
                selectinload(Customer.details),
            )
        )
        return result.scalar_one_or_none()

    async def create_customer(self, body: CustomerCreate, company_id: UUID, user_id: UUID) -> Customer:
        now = datetime.now(timezone.utc)
        exclude = {"addresses", "contacts", "details"}
        c = Customer(
            **{k: v for k, v in body.model_dump(exclude=exclude).items()},
            company_id=company_id,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(c)
        await self.db.flush()
        for a in body.addresses:
            self.db.add(CustomerAddress(customer_id=c.id, **a.model_dump()))
        for ct in body.contacts:
            self.db.add(CustomerContact(customer_id=c.id, created_at=now, updated_at=now, **ct.model_dump()))
        for d in body.details:
            self.db.add(CustomerDetail(customer_id=c.id, created_at=now, updated_at=now, **d.model_dump()))
        await self.db.flush()
        result = await self.db.execute(
            select(Customer).where(Customer.id == c.id)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.contacts),
                selectinload(Customer.details),
            )
        )
        return result.scalar_one()

    async def update_customer(self, cid: UUID, body: CustomerUpdate, company_id: UUID) -> Customer | None:
        c = await self.get_customer(cid, company_id)
        if not c:
            return None
        now = datetime.now(timezone.utc)
        scalar_fields = body.model_dump(exclude_unset=True, exclude={"addresses", "contacts", "details"})
        for f, v in scalar_fields.items():
            setattr(c, f, v)
        c.updated_at = now
        if body.addresses is not None:
            for addr in c.addresses:
                await self.db.delete(addr)
            for a in body.addresses:
                self.db.add(CustomerAddress(customer_id=c.id, **a.model_dump()))
        if body.contacts is not None:
            for ct in c.contacts:
                await self.db.delete(ct)
            for ct in body.contacts:
                self.db.add(CustomerContact(customer_id=c.id, created_at=now, updated_at=now, **ct.model_dump()))
        if body.details is not None:
            for d in c.details:
                await self.db.delete(d)
            for d in body.details:
                self.db.add(CustomerDetail(customer_id=c.id, created_at=now, updated_at=now, **d.model_dump()))
        await self.db.flush()
        result = await self.db.execute(
            select(Customer).where(Customer.id == c.id)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.contacts),
                selectinload(Customer.details),
            )
        )
        return result.scalar_one()

    # ── Quotations ─────────────────────────────────────────────────────────

    async def list_quotations(
        self, company_id: UUID, status: str | None = None,
        customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Quotation], int]:
        q = (
            select(Quotation)
            .where(Quotation.company_id == company_id)
            .options(selectinload(Quotation.customer), selectinload(Quotation.items))
        )
        if status:
            q = q.where(Quotation.status == status)
        if customer_id:
            q = q.where(Quotation.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(Quotation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_quotation(self, qid: UUID, company_id: UUID) -> Quotation | None:
        result = await self.db.execute(
            select(Quotation)
            .where(Quotation.id == qid, Quotation.company_id == company_id)
            .options(selectinload(Quotation.customer), selectinload(Quotation.items))
        )
        return result.scalar_one_or_none()

    async def create_quotation(self, body: QuotationCreate, company_id: UUID, user_id: UUID) -> Quotation:
        now = datetime.now(timezone.utc)
        number = await _next_seq(self.db, "QT", company_id, Quotation)
        q = Quotation(
            company_id=company_id, quotation_number=number, customer_id=body.customer_id,
            quotation_date=body.quotation_date, valid_until=body.valid_until,
            notes=body.notes, terms=body.terms, created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(q)
        await self.db.flush()

        totals = {"subtotal": Decimal("0"), "discount_amount": Decimal("0"),
                  "taxable_amount": Decimal("0"), "cgst_amount": Decimal("0"),
                  "sgst_amount": Decimal("0"), "igst_amount": Decimal("0"), "total_amount": Decimal("0")}

        for i, item_data in enumerate(body.items):
            amounts = _item_amounts(item_data.unit_price, item_data.quantity,
                                    item_data.discount_pct, item_data.gst_rate, body.intrastate)
            self.db.add(QuotationItem(
                quotation_id=q.id, product_id=item_data.product_id, variant_id=item_data.variant_id,
                description=item_data.description, quantity=item_data.quantity, unit_id=item_data.unit_id,
                unit_price=item_data.unit_price, discount_pct=item_data.discount_pct,
                gst_rate=item_data.gst_rate, hsn_code=item_data.hsn_code,
                sort_order=item_data.sort_order or i, **amounts,
            ))
            gross = (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
            totals["subtotal"] += gross
            for k in ("discount_amount", "taxable_amount", "cgst_amount", "sgst_amount", "igst_amount", "total_amount"):
                totals[k] += amounts[k]

        for k, v in totals.items():
            setattr(q, k, v)
        await self.db.flush()

        result = await self.db.execute(
            select(Quotation).where(Quotation.id == q.id)
            .options(selectinload(Quotation.customer), selectinload(Quotation.items))
        )
        return result.scalar_one()

    async def update_quotation(self, qid: UUID, body: QuotationUpdate, company_id: UUID) -> Quotation | None:
        q = await self.get_quotation(qid, company_id)
        if not q or q.status not in ("draft", "sent"):
            return None
        for f, v in body.model_dump(exclude_unset=True).items():
            setattr(q, f, v)
        q.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return q

    async def send_quotation(self, qid: UUID, company_id: UUID) -> Quotation | None:
        q = await self.get_quotation(qid, company_id)
        if not q or q.status != "draft":
            return None
        q.status = "sent"
        q.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return q

    async def approve_quotation(self, qid: UUID, company_id: UUID, user_id: UUID) -> Quotation | None:
        q = await self.get_quotation(qid, company_id)
        if not q or q.status not in ("draft", "sent"):
            return None
        q.status = "approved"
        q.approved_by = user_id
        q.approved_at = datetime.now(timezone.utc)
        q.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return q

    async def convert_quotation_to_so(
        self, qid: UUID, company_id: UUID, user_id: UUID, order_date: date,
        expected_delivery: date | None, intrastate: bool,
    ) -> SalesOrder | None:
        q = await self.get_quotation(qid, company_id)
        if not q or q.status not in ("draft", "sent", "approved"):
            return None

        so = await self.create_sales_order(
            SalesOrderCreate(
                customer_id=q.customer_id, quotation_id=q.id,
                order_date=order_date, expected_delivery=expected_delivery,
                notes=q.notes, intrastate=intrastate,
                items=[
                    type("SOItem", (), {
                        "product_id": i.product_id, "variant_id": i.variant_id,
                        "quantity": i.quantity, "unit_id": i.unit_id,
                        "unit_price": i.unit_price, "discount_pct": i.discount_pct,
                        "gst_rate": i.gst_rate, "hsn_code": i.hsn_code,
                    })()
                    for i in q.items
                ],
            ),
            company_id, user_id, intrastate=intrastate,
        )
        q.status = "converted"
        q.converted_order_id = so.id
        q.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return so

    # ── Sales Orders ───────────────────────────────────────────────────────

    async def list_sales_orders(
        self, company_id: UUID, status: str | None = None,
        customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[SalesOrder], int]:
        q = (
            select(SalesOrder)
            .where(SalesOrder.company_id == company_id)
            .options(selectinload(SalesOrder.customer), selectinload(SalesOrder.items))
        )
        if status:
            q = q.where(SalesOrder.status == status)
        if customer_id:
            q = q.where(SalesOrder.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(SalesOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_sales_order(self, so_id: UUID, company_id: UUID) -> SalesOrder | None:
        result = await self.db.execute(
            select(SalesOrder)
            .where(SalesOrder.id == so_id, SalesOrder.company_id == company_id)
            .options(selectinload(SalesOrder.customer), selectinload(SalesOrder.items))
        )
        return result.scalar_one_or_none()

    async def get_committed_quantity(
        self, company_id: UUID, product_id: UUID, variant_id: UUID | None = None,
    ) -> Decimal:
        """Outstanding (undelivered) quantity committed across all open Sales
        Orders for a product/variant - ERP Upgrade §2's 'already committed to
        other orders'. Cancelled orders are excluded; delivered_qty is kept
        current by create_delivery(), so this is a live aggregate, not a
        separate reservation ledger."""
        result = await self.db.execute(
            text("""
                SELECT COALESCE(SUM(GREATEST(soi.quantity - soi.delivered_qty, 0)), 0)
                FROM sales_order_items soi
                JOIN sales_orders so ON so.id = soi.sales_order_id
                WHERE so.company_id = :company_id
                  AND so.status != 'cancelled'
                  AND soi.product_id = :product_id
                  AND (CAST(:variant_id AS UUID) IS NULL OR soi.variant_id = CAST(:variant_id AS UUID))
            """),
            {
                "company_id": str(company_id),
                "product_id": str(product_id),
                "variant_id": str(variant_id) if variant_id else None,
            },
        )
        return Decimal(result.scalar() or 0)

    async def create_sales_order(
        self, body: SalesOrderCreate, company_id: UUID, user_id: UUID, intrastate: bool = True,
    ) -> SalesOrder:
        now = datetime.now(timezone.utc)

        # ERP Upgrade §5: validate against the customer PO's quantity
        # tolerance BEFORE creating any row, so a rejected order leaves no
        # partial state. Only runs when a PO quantity was actually given -
        # a Sales Order "may" reference a PO, it isn't required to.
        if body.customer_po_quantity:
            total_qty = sum(item.quantity for item in body.items)
            result = business_rules.validate_po_quantity(
                body.customer_po_quantity, total_qty, body.po_tolerance_pct or Decimal("5"),
            )
            if not result.valid:
                raise BusinessRulesError("PO_QUANTITY_TOLERANCE", result.reason)

        number = await _next_seq(self.db, "SO", company_id, SalesOrder)
        so = SalesOrder(
            company_id=company_id, order_number=number, customer_id=body.customer_id,
            quotation_id=body.quotation_id, order_date=body.order_date,
            expected_delivery=body.expected_delivery, notes=body.notes,
            customer_po_number=body.customer_po_number, customer_po_quantity=body.customer_po_quantity,
            po_tolerance_pct=body.po_tolerance_pct,
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(so)
        await self.db.flush()

        totals = {k: Decimal("0") for k in ("subtotal", "discount_amount", "taxable_amount",
                                              "cgst_amount", "sgst_amount", "igst_amount", "total_amount")}
        use_intrastate = getattr(body, "intrastate", intrastate)

        for item_data in body.items:
            amounts = _item_amounts(item_data.unit_price, item_data.quantity,
                                    item_data.discount_pct, item_data.gst_rate, use_intrastate)
            self.db.add(SalesOrderItem(
                sales_order_id=so.id, product_id=item_data.product_id,
                variant_id=item_data.variant_id, quantity=item_data.quantity,
                unit_id=item_data.unit_id, unit_price=item_data.unit_price,
                discount_pct=item_data.discount_pct, gst_rate=item_data.gst_rate,
                hsn_code=item_data.hsn_code, **amounts,
            ))
            totals["subtotal"] += (item_data.unit_price * item_data.quantity).quantize(Decimal("0.01"))
            for k in ("discount_amount", "taxable_amount", "cgst_amount", "sgst_amount", "igst_amount", "total_amount"):
                totals[k] += amounts[k]

        for k, v in totals.items():
            setattr(so, k, v)
        await self.db.flush()

        result = await self.db.execute(
            select(SalesOrder).where(SalesOrder.id == so.id)
            .options(selectinload(SalesOrder.customer), selectinload(SalesOrder.items))
        )
        return result.scalar_one()

    async def cancel_sales_order(self, so_id: UUID, company_id: UUID) -> SalesOrder | None:
        so = await self.get_sales_order(so_id, company_id)
        if not so or so.status not in ("confirmed", "processing"):
            return None
        so.status = "cancelled"
        so.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return so

    # ── Deliveries ─────────────────────────────────────────────────────────

    async def list_deliveries(
        self, company_id: UUID, status: str | None = None,
        sales_order_id: UUID | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Delivery], int]:
        q = (
            select(Delivery)
            .where(Delivery.company_id == company_id)
            .options(selectinload(Delivery.customer), selectinload(Delivery.items))
        )
        if status:
            q = q.where(Delivery.status == status)
        if sales_order_id:
            q = q.where(Delivery.sales_order_id == sales_order_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(Delivery.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_delivery(self, did: UUID, company_id: UUID) -> Delivery | None:
        result = await self.db.execute(
            select(Delivery)
            .where(Delivery.id == did, Delivery.company_id == company_id)
            .options(
                selectinload(Delivery.customer).selectinload(Customer.addresses),
                selectinload(Delivery.items),
                selectinload(Delivery.sales_order),
            )
        )
        return result.scalar_one_or_none()

    async def list_sales_returns_for_delivery(self, delivery_id: UUID, company_id: UUID) -> list[SalesReturn]:
        result = await self.db.execute(
            select(SalesReturn)
            .where(SalesReturn.delivery_id == delivery_id, SalesReturn.company_id == company_id)
            .options(selectinload(SalesReturn.items))
        )
        return result.scalars().all()

    async def create_delivery(self, body: DeliveryCreate, company_id: UUID, user_id: UUID) -> Delivery:
        now = datetime.now(timezone.utc)
        number = await _next_seq(self.db, "DC", company_id, Delivery)

        # Fetch SO to get customer_id
        so_result = await self.db.execute(
            select(SalesOrder).where(SalesOrder.id == body.sales_order_id, SalesOrder.company_id == company_id)
        )
        so = so_result.scalar_one_or_none()
        if not so:
            raise ValueError("Sales order not found")

        d = Delivery(
            company_id=company_id, delivery_number=number, sales_order_id=body.sales_order_id,
            customer_id=so.customer_id, warehouse_id=body.warehouse_id,
            delivery_date=body.delivery_date, purpose=body.purpose, transporter=body.transporter,
            lr_number=body.lr_number, vehicle_number=body.vehicle_number,
            notes=body.notes, status="dispatched", dispatched_at=now,
            carton_count=body.carton_count, package_count=body.package_count,
            packing_marks=body.packing_marks, gross_weight=body.gross_weight,
            net_weight=body.net_weight,
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(d)
        await self.db.flush()

        for item_data in body.items:
            # Value the stock leaving at its real production cost, not the
            # customer's selling price (item_data.unit_price is kept separately
            # on DeliveryItem.unit_price below for revenue/invoicing).
            cost = await self.inv.get_weighted_avg_cost(
                company_id, item_data.product_id, body.warehouse_id, item_data.variant_id,
            )
            inv_txn = await self.inv.issue(
                IssueParams(
                    company_id=company_id, product_id=item_data.product_id,
                    variant_id=item_data.variant_id, warehouse_id=body.warehouse_id,
                    lot_id=item_data.lot_id,
                    quantity=item_data.quantity, unit_id=item_data.unit_id,
                    unit_cost=cost, material_type="finished_good",
                    transaction_date=body.delivery_date, reference_type="delivery",
                    reference_id=d.id, notes=f"DC {number}",
                ),
                user_id=user_id,
            )
            await self.db.flush()

            self.db.add(DeliveryItem(
                delivery_id=d.id, so_item_id=item_data.so_item_id,
                product_id=item_data.product_id, variant_id=item_data.variant_id,
                lot_id=inv_txn.lot_id,
                quantity=item_data.quantity, unit_id=item_data.unit_id,
                unit_price=item_data.unit_price,
                total_amount=(item_data.unit_price * item_data.quantity).quantize(Decimal("0.01")),
                inv_transaction_id=inv_txn.id,
                returnable=item_data.returnable, weight_kg=item_data.weight_kg,
            ))

            # Update SO item delivered_qty
            so_item_res = await self.db.execute(
                select(SalesOrderItem).where(SalesOrderItem.id == item_data.so_item_id)
            )
            so_item = so_item_res.scalar_one_or_none()
            if so_item:
                so_item.delivered_qty += item_data.quantity

        await self.db.flush()

        # Update SO status
        so_items_res = await self.db.execute(
            select(SalesOrderItem).where(SalesOrderItem.sales_order_id == body.sales_order_id)
        )
        so_items = so_items_res.scalars().all()
        if so_items:
            fully = all(i.delivered_qty >= i.quantity for i in so_items)
            so.status = "completed" if fully else "partial"
            so.updated_at = now

        await self.db.flush()

        result = await self.db.execute(
            select(Delivery).where(Delivery.id == d.id)
            .options(selectinload(Delivery.customer), selectinload(Delivery.items))
        )
        return result.scalar_one()

    # ── Sales Returns ────────────────────────────────────────────────────────
    # Customer returning finished goods — distinct from the raw-material MIS
    # return (production -> warehouse). Double-credit protection mirrors the
    # MIS-return pattern: rather than a single running counter, each new
    # return's quantity is checked against SUM(prior returns) for the same
    # delivery_item_id, so the same remainder can never be returned twice.

    async def list_sales_returns(
        self, company_id: UUID, customer_id: UUID | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[SalesReturn], int]:
        q = (
            select(SalesReturn)
            .where(SalesReturn.company_id == company_id)
            .options(selectinload(SalesReturn.customer), selectinload(SalesReturn.items))
        )
        if customer_id:
            q = q.where(SalesReturn.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(SalesReturn.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_sales_return(self, rid: UUID, company_id: UUID) -> SalesReturn | None:
        result = await self.db.execute(
            select(SalesReturn)
            .where(SalesReturn.id == rid, SalesReturn.company_id == company_id)
            .options(selectinload(SalesReturn.customer), selectinload(SalesReturn.items))
        )
        return result.scalar_one_or_none()

    async def create_sales_return(
        self, body: SalesReturnCreate, company_id: UUID, user_id: UUID,
    ) -> SalesReturn:
        now = datetime.now(timezone.utc)
        number = await _next_seq(self.db, "SR", company_id, SalesReturn)

        r = SalesReturn(
            company_id=company_id, return_number=number, delivery_id=body.delivery_id,
            customer_id=body.customer_id, return_date=body.return_date, reason=body.reason,
            notes=body.notes, status="completed",
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(r)
        await self.db.flush()

        for item_data in body.items:
            delivery_item: DeliveryItem | None = None
            delivery_warehouse_id: UUID | None = None
            if item_data.delivery_item_id:
                di_res = await self.db.execute(
                    select(DeliveryItem, Delivery.warehouse_id).join(Delivery)
                    .where(DeliveryItem.id == item_data.delivery_item_id, Delivery.company_id == company_id)
                )
                row = di_res.first()
                if not row:
                    raise QuantityValidationError("Referenced delivery line not found.")
                delivery_item, delivery_warehouse_id = row
                if not delivery_item.returnable:
                    raise QuantityValidationError("This delivery line is marked non-returnable.")

                already_returned = (await self.db.execute(
                    select(func.coalesce(func.sum(SalesReturnItem.quantity), 0))
                    .where(SalesReturnItem.delivery_item_id == item_data.delivery_item_id)
                )).scalar() or Decimal("0")
                if already_returned + item_data.quantity > delivery_item.quantity:
                    raise QuantityValidationError(
                        f"Cannot return more than was delivered on this line "
                        f"(delivered: {delivery_item.quantity}, already returned: {already_returned}, "
                        f"requested: {item_data.quantity})."
                    )

            restocks = item_data.disposition in ("usable_stock", "resale_stock")
            warehouse_id = item_data.warehouse_id or delivery_warehouse_id
            if restocks and not warehouse_id:
                raise QuantityValidationError(
                    "A warehouse is required to credit stock back for usable_stock/resale_stock "
                    "returns that aren't linked to a delivery line."
                )

            if restocks:
                unit_cost = await self.inv.get_weighted_avg_cost(
                    company_id, item_data.product_id, warehouse_id, item_data.variant_id,
                )
            else:
                # Scrap/wastage carries no inventory value - tracked for
                # record-keeping only, never inflates sellable stock value.
                unit_cost = Decimal("0")
            total_cost = (unit_cost * item_data.quantity).quantize(Decimal("0.01"))

            inv_txn_id = None
            if restocks:
                inv_txn = await self.inv.receive(
                    ReceiveParams(
                        company_id=company_id, product_id=item_data.product_id,
                        variant_id=item_data.variant_id, warehouse_id=warehouse_id,
                        quantity=item_data.quantity, unit_id=item_data.unit_id,
                        unit_cost=unit_cost, material_type="finished_good",
                        transaction_date=body.return_date, reference_type="sales_return",
                        reference_id=r.id, notes=f"Return against {number}",
                    ),
                    user_id=user_id,
                )
                inv_txn_id = inv_txn.id

            self.db.add(SalesReturnItem(
                sales_return_id=r.id, delivery_item_id=item_data.delivery_item_id,
                product_id=item_data.product_id, variant_id=item_data.variant_id,
                quantity=item_data.quantity, unit_id=item_data.unit_id,
                disposition=item_data.disposition, unit_cost=unit_cost, total_cost=total_cost,
                inv_transaction_id=inv_txn_id, notes=item_data.notes,
            ))

        await self.db.flush()
        result = await self.db.execute(
            select(SalesReturn).where(SalesReturn.id == r.id)
            .options(selectinload(SalesReturn.customer), selectinload(SalesReturn.items))
        )
        return result.scalar_one()

    # ── Invoices ───────────────────────────────────────────────────────────

    async def list_invoices(
        self, company_id: UUID, status: str | None = None,
        customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Invoice], int]:
        q = (
            select(Invoice)
            .where(Invoice.company_id == company_id)
            .options(selectinload(Invoice.customer))
        )
        if status:
            q = q.where(Invoice.status == status)
        if customer_id:
            q = q.where(Invoice.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_invoice(self, inv_id: UUID, company_id: UUID) -> Invoice | None:
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.id == inv_id, Invoice.company_id == company_id)
            .options(selectinload(Invoice.customer))
        )
        return result.scalar_one_or_none()

    async def create_invoice_from_delivery(
        self, body: InvoiceCreate, company_id: UUID, user_id: UUID,
    ) -> Invoice:
        now = datetime.now(timezone.utc)
        number = await _next_seq(self.db, "INV", company_id, Invoice)

        # Pull amounts from delivery's SO if delivery is provided
        subtotal = taxable = cgst = sgst = igst = total = Decimal("0")

        if body.delivery_id:
            d_res = await self.db.execute(
                select(Delivery).where(Delivery.id == body.delivery_id, Delivery.company_id == company_id)
                .options(selectinload(Delivery.items))
            )
            delivery = d_res.scalar_one_or_none()
            if delivery:
                # Tax comes from the order lines, pro-rated by delivered quantity -
                # a delivery line carries no GST of its own, so summing delivery
                # totals silently under-billed tax on every invoice.
                so_item_ids = {i.so_item_id for i in delivery.items}
                so_items = {
                    si.id: si for si in (await self.db.execute(
                        select(SalesOrderItem).where(SalesOrderItem.id.in_(so_item_ids))
                    )).scalars().all()
                }
                for item in delivery.items:
                    si = so_items.get(item.so_item_id)
                    if si is None or si.quantity <= 0:
                        continue
                    fraction = item.quantity / si.quantity
                    subtotal += si.unit_price * item.quantity
                    taxable += si.taxable_amount * fraction
                    cgst += si.cgst_amount * fraction
                    sgst += si.sgst_amount * fraction
                    igst += si.igst_amount * fraction
                total = taxable + cgst + sgst + igst

        if body.sales_order_id and taxable == Decimal("0"):
            so_res = await self.db.execute(
                select(SalesOrder).where(SalesOrder.id == body.sales_order_id, SalesOrder.company_id == company_id)
            )
            so = so_res.scalar_one_or_none()
            if so:
                subtotal = so.subtotal
                taxable = so.taxable_amount
                cgst = so.cgst_amount
                sgst = so.sgst_amount
                igst = so.igst_amount
                total = so.total_amount

        inv = Invoice(
            company_id=company_id, invoice_number=number, customer_id=body.customer_id,
            sales_order_id=body.sales_order_id, delivery_id=body.delivery_id,
            invoice_date=body.invoice_date, due_date=body.due_date, notes=body.notes,
            subtotal=subtotal, taxable_amount=taxable,
            cgst_amount=cgst, sgst_amount=sgst, igst_amount=igst,
            total_amount=total, balance_amount=total,
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(inv)
        await self.db.flush()

        result = await self.db.execute(
            select(Invoice).where(Invoice.id == inv.id).options(selectinload(Invoice.customer))
        )
        return result.scalar_one()
