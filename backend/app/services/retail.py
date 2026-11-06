"""Retail Sales: counter bills, estimates, retail customers and collections.

Money rules (see models/retail.py):
- Prices are GST-inclusive. Line net = MRP x qty, less the item discount,
  less the bill discount on what's left. GST is backed out of the net.
- Discounts must be 0 or between the configured minimum and maximum, per
  line, per bill and combined. Above the maximum only a user with
  retail.discount_approve may bill (recorded as the approver), and only
  when the settings allow it. The price is the master MRP, so a discount
  can't be slipped in by typing a lower price.
- A bill's value is a sale on its date; money received later against a
  credit bill is a collection, never a second sale.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.business_rules import BusinessRulesError
from app.models.master import Product, ProductVariant, Warehouse
from app.models.retail import (
    RetailCustomer, RetailEstimate, RetailEstimateItem, RetailInvoice, RetailInvoiceItem,
    RetailPayment, RetailSettings, RetailSettingsAudit,
)
from app.schemas.inventory import IssueParams, ReceiveParams
from app.schemas.retail import (
    RetailCustomerCreate, RetailCustomerUpdate, RetailEstimateConvert, RetailEstimateCreate,
    RetailInvoiceCreate, RetailLineIn, RetailPaymentCreate, RetailSettingsUpdate,
)
from app.services.inventory import InventoryService

CENT = Decimal("0.01")
HUNDRED = Decimal("100")
# Clothing GST when a product has no HSN code: 5% up to ₹2,500 taxable value
# per piece, 18% above (rates in force from 22 Sep 2025).
APPAREL_GST_THRESHOLD = Decimal("2500")


def _q(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


def _apparel_gst(unit_price_incl: Decimal) -> Decimal:
    return Decimal("5") if unit_price_incl / Decimal("1.05") <= APPAREL_GST_THRESHOLD else Decimal("18")


def _payment_status(total: Decimal, paid: Decimal) -> str:
    if paid >= total:
        return "paid"
    return "partially_paid" if paid > 0 else "unpaid"


class RetailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    # ── Numbering ──────────────────────────────────────────────────────────

    async def _next_number(self, model, column, prefix: str, company_id: UUID) -> str:
        """Next number in this document's own series (RE / RI / RR)."""
        last = (await self.db.execute(
            select(func.max(column)).where(model.company_id == company_id, column.like(f"{prefix}%"))
        )).scalar()
        seq = int(last[len(prefix):]) + 1 if last and last[len(prefix):].isdigit() else 1
        return f"{prefix}{seq:05d}"

    # ── Settings ───────────────────────────────────────────────────────────

    async def get_settings(self, company_id: UUID) -> RetailSettings:
        s = await self.db.get(RetailSettings, company_id)
        if s is None:
            wh = (await self.db.execute(
                select(Warehouse.id).where(Warehouse.company_id == company_id)
                .order_by((Warehouse.material_type == "finished_good").desc().nulls_last(),
                          (Warehouse.code == "WH-FG").desc(), Warehouse.name)
                .limit(1)
            )).scalar_one_or_none()
            s = RetailSettings(
                company_id=company_id, warehouse_id=wh, min_discount_pct=Decimal("0"),
                max_discount_pct=Decimal("10"), default_discount_pct=Decimal("0"),
                allow_approved_override=True, credit_days=30, estimate_validity_days=7,
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(s)
            await self.db.flush()
        return s

    async def update_settings(self, body: RetailSettingsUpdate, company_id: UUID, user_id: UUID) -> RetailSettings:
        s = await self.get_settings(company_id)
        changes = body.model_dump(exclude_unset=True)
        new = {f: changes.get(f, getattr(s, f)) for f in ("min_discount_pct", "max_discount_pct", "default_discount_pct")}
        if new["min_discount_pct"] > new["max_discount_pct"]:
            raise BusinessRulesError("BAD_LIMITS", "Minimum discount can't be more than the maximum.")
        default = new["default_discount_pct"]
        if default and not (new["min_discount_pct"] <= default <= new["max_discount_pct"]):
            raise BusinessRulesError("BAD_LIMITS", "Default discount must be 0 or between the minimum and maximum.")
        if "warehouse_id" in changes and changes["warehouse_id"]:
            ok = (await self.db.execute(
                select(Warehouse.id).where(Warehouse.id == changes["warehouse_id"], Warehouse.company_id == company_id)
            )).scalar_one_or_none()
            if not ok:
                raise BusinessRulesError("NOT_FOUND", "Warehouse not found")
        now = datetime.now(timezone.utc)
        for field, value in changes.items():
            old = getattr(s, field)
            if old == value:
                continue
            self.db.add(RetailSettingsAudit(
                company_id=company_id, field=field,
                old_value=None if old is None else str(old), new_value=None if value is None else str(value),
                changed_by=user_id, changed_at=now,
            ))
            setattr(s, field, value)
        s.updated_at, s.updated_by = now, user_id
        await self.db.flush()
        return s

    async def settings_audit(self, company_id: UUID, limit: int = 50) -> list[RetailSettingsAudit]:
        return (await self.db.execute(
            select(RetailSettingsAudit).where(RetailSettingsAudit.company_id == company_id)
            .order_by(RetailSettingsAudit.changed_at.desc()).limit(limit)
        )).scalars().all()

    # ── Customers ──────────────────────────────────────────────────────────

    _CUSTOMER_STATS = """
        SELECT c.id,
               COUNT(i.id) AS purchase_count,
               COALESCE(SUM(i.total_amount), 0) AS total_spent,
               COALESCE(SUM(q.qty), 0) AS products_purchased,
               MAX(i.invoice_date) AS last_purchase_date,
               COALESCE(SUM(i.total_amount - i.amount_paid), 0) AS outstanding
        FROM retail_customers c
        LEFT JOIN retail_invoices i ON i.customer_id = c.id AND i.status = 'active'
        LEFT JOIN (SELECT invoice_id, SUM(quantity) AS qty FROM retail_invoice_items GROUP BY invoice_id) q
               ON q.invoice_id = i.id
        WHERE c.company_id = :cid {where}
        GROUP BY c.id
    """

    async def customer_stats(self, company_id: UUID, customer_ids: list[UUID] | None = None) -> dict[UUID, dict]:
        where = "AND c.id = ANY(:ids)" if customer_ids is not None else ""
        params: dict = {"cid": str(company_id)}
        if customer_ids is not None:
            params["ids"] = [str(i) for i in customer_ids]
        rows = (await self.db.execute(text(self._CUSTOMER_STATS.format(where=where)), params)).mappings().all()
        return {r["id"]: dict(r) for r in rows}

    async def list_customers(
        self, company_id: UUID, search: str | None = None, city: str | None = None,
        birthday_month: int | None = None, sort: str = "recent", status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[tuple[RetailCustomer, dict]], int]:
        filters = ["c.company_id = :cid"]
        params: dict = {"cid": str(company_id)}
        if search:
            filters.append("(c.name ILIKE :s OR c.mobile LIKE :s OR c.email ILIKE :s)")
            params["s"] = f"%{search.strip()}%"
        if city:
            filters.append("c.city ILIKE :city")
            params["city"] = city.strip()
        if birthday_month:
            filters.append("EXTRACT(MONTH FROM c.date_of_birth) = :bm")
            params["bm"] = birthday_month
        if status:
            filters.append("c.status = :status")
            params["status"] = status
        order = {
            "frequent": "purchase_count DESC, total_spent DESC",
            "spending": "total_spent DESC",
            "recent": "last_purchase_date DESC NULLS LAST, c.created_at DESC",
            "lapsed": "last_purchase_date ASC NULLS FIRST",
            "products": "products_purchased DESC",
            "outstanding": "outstanding DESC",
            "name": "c.name",
            "newest": "c.created_at DESC",
        }.get(sort, "c.created_at DESC")
        base = f"""
            SELECT c.id,
                   COUNT(i.id) AS purchase_count,
                   COALESCE(SUM(i.total_amount), 0) AS total_spent,
                   COALESCE(SUM(q.qty), 0) AS products_purchased,
                   MAX(i.invoice_date) AS last_purchase_date,
                   COALESCE(SUM(i.total_amount - i.amount_paid), 0) AS outstanding
            FROM retail_customers c
            LEFT JOIN retail_invoices i ON i.customer_id = c.id AND i.status = 'active'
            LEFT JOIN (SELECT invoice_id, SUM(quantity) AS qty FROM retail_invoice_items GROUP BY invoice_id) q
                   ON q.invoice_id = i.id
            WHERE {" AND ".join(filters)}
            GROUP BY c.id
        """
        total = (await self.db.execute(text(f"SELECT COUNT(*) FROM ({base}) t"), params)).scalar() or 0
        rows = (await self.db.execute(
            text(f"{base} ORDER BY {order} LIMIT :lim OFFSET :off"),
            {**params, "lim": page_size, "off": (page - 1) * page_size},
        )).mappings().all()
        ids = [r["id"] for r in rows]
        customers = {c.id: c for c in (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.id.in_(ids))
        )).scalars().all()} if ids else {}
        return [(customers[r["id"]], dict(r)) for r in rows], total

    async def get_customer(self, customer_id: UUID, company_id: UUID) -> RetailCustomer | None:
        return (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.id == customer_id, RetailCustomer.company_id == company_id)
        )).scalar_one_or_none()

    async def find_by_mobile(self, mobile: str, company_id: UUID) -> RetailCustomer | None:
        return (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.company_id == company_id, RetailCustomer.mobile == mobile)
        )).scalar_one_or_none()

    async def create_customer(self, body: RetailCustomerCreate, company_id: UUID, user_id: UUID) -> RetailCustomer:
        existing = await self.find_by_mobile(body.mobile, company_id)
        if existing:
            raise BusinessRulesError("DUPLICATE_MOBILE", f"{existing.name} is already registered with mobile {body.mobile}")
        data = {k: (v.strip() or None) if isinstance(v, str) else v for k, v in body.model_dump().items()}
        data["name"] = body.name.strip()
        c = RetailCustomer(company_id=company_id, created_by=user_id, created_at=datetime.now(timezone.utc), **data)
        self.db.add(c)
        await self.db.flush()
        return c

    async def update_customer(self, customer_id: UUID, body: RetailCustomerUpdate, company_id: UUID) -> RetailCustomer | None:
        c = await self.get_customer(customer_id, company_id)
        if not c:
            return None
        changes = body.model_dump(exclude_unset=True)
        if changes.get("mobile") and changes["mobile"] != c.mobile:
            other = await self.find_by_mobile(changes["mobile"], company_id)
            if other:
                raise BusinessRulesError("DUPLICATE_MOBILE", f"{other.name} is already registered with mobile {changes['mobile']}")
        for k, v in changes.items():
            setattr(c, k, (v.strip() or None) if isinstance(v, str) and k != "name" else v)
        c.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return c

    # ── Products for the billing search ────────────────────────────────────

    async def search_products(self, company_id: UUID, search: str, limit: int = 30) -> list[dict]:
        settings = await self.get_settings(company_id)
        # One row per size/colour variant, plus a product-level row for stock
        # recorded without a size (e.g. production output) or a product
        # that has no variants at all.
        rows = (await self.db.execute(text("""
            WITH matched AS (
                SELECT p.* FROM products p
                WHERE p.company_id = :cid AND p.product_type = 'finished_good' AND p.is_active
                  AND p.deleted_at IS NULL AND p.merged_into_id IS NULL
                  AND (:s = '' OR p.name ILIKE :like OR p.code ILIKE :like OR EXISTS (
                        SELECT 1 FROM product_variants v WHERE v.product_id = p.id
                          AND (v.sku ILIKE :like OR v.barcode = :s)))
            ), sellable AS (
                SELECT p.id AS product_id, v.id AS variant_id, p.name, v.sku, v.barcode,
                       sz.name AS size, co.name AS colour, COALESCE(v.mrp, p.mrp) AS mrp, p.hsn_id,
                       (v.barcode = :s) AS barcode_hit,
                       COALESCE((SELECT SUM(t.quantity * t.direction) FROM inventory_transactions t
                                 WHERE t.product_id = p.id AND t.warehouse_id = CAST(:wh AS UUID)
                                   AND t.variant_id = v.id), 0) AS in_stock
                FROM matched p
                JOIN product_variants v ON v.product_id = p.id AND v.is_active
                LEFT JOIN sizes sz ON sz.id = v.size_id
                LEFT JOIN colours co ON co.id = v.colour_id
                WHERE :s = '' OR p.name ILIKE :like OR p.code ILIKE :like OR v.sku ILIKE :like OR v.barcode = :s
                UNION ALL
                SELECT p.id, NULL, p.name, NULL, NULL, NULL, NULL, p.mrp, p.hsn_id, FALSE,
                       COALESCE((SELECT SUM(t.quantity * t.direction) FROM inventory_transactions t
                                 WHERE t.product_id = p.id AND t.warehouse_id = CAST(:wh AS UUID)
                                   AND t.variant_id IS NULL), 0)
                FROM matched p
            )
            SELECT s.product_id, s.variant_id, s.name, s.sku, s.barcode, s.size, s.colour, s.mrp,
                   h.gst_rate, h.hsn AS hsn_code, s.in_stock
            FROM sellable s
            LEFT JOIN hsn_codes h ON h.id = s.hsn_id
            WHERE s.variant_id IS NOT NULL OR s.in_stock <> 0
               OR NOT EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id = s.product_id AND v.is_active)
            ORDER BY COALESCE(s.barcode_hit, FALSE) DESC, (s.in_stock > 0) DESC, s.name, s.size NULLS FIRST
            LIMIT :lim
        """), {"cid": str(company_id), "wh": str(settings.warehouse_id) if settings.warehouse_id else None,
               "s": search.strip(), "like": f"%{search.strip()}%", "lim": limit})).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            mrp = d["mrp"]
            d["gst_rate"] = d["gst_rate"] if d["gst_rate"] is not None else (_apparel_gst(mrp) if mrp else Decimal("5"))
            out.append(d)
        return out

    # ── Pricing a bill ─────────────────────────────────────────────────────

    async def _price(
        self, lines: list[RetailLineIn], bill_discount_pct: Decimal, company_id: UUID,
        user_id: UUID, can_approve: bool,
    ) -> tuple[list[dict], dict]:
        """Lines and totals for a bill or estimate, after checking discounts."""
        settings = await self.get_settings(company_id)
        lo, hi = settings.min_discount_pct, settings.max_discount_pct
        needs_approval = False

        def check(pct: Decimal, what: str) -> None:
            nonlocal needs_approval
            if pct and pct < lo:
                raise BusinessRulesError("DISCOUNT_TOO_LOW", f"{what} discount must be 0 or at least {lo}%.")
            if pct > hi:
                needs_approval = True

        bill = Decimal(bill_discount_pct)
        check(bill, "Bill")
        products = {p.id: p for p in (await self.db.execute(
            select(Product).where(Product.company_id == company_id, Product.id.in_({l.product_id for l in lines}))
            .options(selectinload(Product.hsn), selectinload(Product.variants))
        )).scalars().all()}
        variant_ids = {l.variant_id for l in lines if l.variant_id}
        variants = {v.id: v for v in (await self.db.execute(
            select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
            .options(selectinload(ProductVariant.size), selectinload(ProductVariant.colour))
        )).scalars().all()} if variant_ids else {}

        priced: list[dict] = []
        for i, line in enumerate(lines):
            product = products.get(line.product_id)
            if not product or product.deleted_at is not None:
                raise BusinessRulesError("NOT_FOUND", "A product on this bill was not found")
            variant = variants.get(line.variant_id) if line.variant_id else None
            if line.variant_id and (not variant or variant.product_id != product.id):
                raise BusinessRulesError("NOT_FOUND", f"Size/colour not found for {product.name}")
            mrp = (variant.mrp if variant else None) or product.mrp
            price = Decimal(mrp) if mrp else line.unit_price
            if not price:
                raise BusinessRulesError("PRICE_REQUIRED", f"{product.name} has no MRP — enter its price")
            item_pct = Decimal(line.item_discount_pct)
            check(item_pct, "Item")
            combined = HUNDRED - (HUNDRED - item_pct) * (HUNDRED - bill) / HUNDRED
            if combined > hi:
                needs_approval = True
            qty = Decimal(line.quantity)
            gross = _q(price * qty)
            after_item = _q(gross * (HUNDRED - item_pct) / HUNDRED)
            net = _q(after_item * (HUNDRED - bill) / HUNDRED)
            gst_rate = Decimal(product.hsn.gst_rate) if product.hsn else _apparel_gst(price)
            taxable = _q(net * HUNDRED / (HUNDRED + gst_rate))
            gst = net - taxable
            cgst = _q(gst / 2)
            label = product.name
            if variant:
                bits = [b for b in (variant.size.name if variant.size else None, variant.colour.name if variant.colour else None) if b]
                label = f"{product.name} ({' / '.join(bits)})" if bits else f"{product.name} ({variant.sku})"
            priced.append({
                "product_id": product.id, "variant_id": variant.id if variant else None,
                "description": label[:300], "hsn_code": product.hsn.hsn if product.hsn else None,
                "quantity": qty, "unit_price": _q(price), "gross_amount": gross,
                "item_discount_pct": item_pct, "discount_amount": gross - net, "gst_rate": gst_rate,
                "taxable_amount": taxable, "cgst_amount": cgst, "sgst_amount": gst - cgst,
                "net_amount": net, "sort_order": i, "unit_id": product.unit_id,
            })

        if needs_approval and not (can_approve and settings.allow_approved_override):
            raise BusinessRulesError(
                "DISCOUNT_TOO_HIGH",
                f"Discount above the {hi}% maximum needs a manager's approval."
                if settings.allow_approved_override else f"Discount can't be more than {hi}%.",
            )
        exact = sum((l["net_amount"] for l in priced), Decimal("0"))
        total = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        totals = {
            "bill_discount_pct": bill,
            "gross_amount": sum((l["gross_amount"] for l in priced), Decimal("0")),
            "discount_amount": sum((l["discount_amount"] for l in priced), Decimal("0")),
            "taxable_amount": sum((l["taxable_amount"] for l in priced), Decimal("0")),
            "cgst_amount": sum((l["cgst_amount"] for l in priced), Decimal("0")),
            "sgst_amount": sum((l["sgst_amount"] for l in priced), Decimal("0")),
            "round_off": total - exact,
            "total_amount": total,
            "discount_approved_by": user_id if needs_approval else None,
        }
        return priced, totals

    # ── Invoices ───────────────────────────────────────────────────────────

    def _invoice_query(self):
        return select(RetailInvoice).options(
            selectinload(RetailInvoice.items), selectinload(RetailInvoice.payments),
            selectinload(RetailInvoice.customer),
        )

    async def get_invoice(self, invoice_id: UUID, company_id: UUID) -> RetailInvoice | None:
        return (await self.db.execute(
            self._invoice_query().where(RetailInvoice.id == invoice_id, RetailInvoice.company_id == company_id)
        )).scalar_one_or_none()

    async def list_invoices(
        self, company_id: UUID, search: str | None = None, payment_mode: str | None = None,
        payment_status: str | None = None, customer_id: UUID | None = None,
        from_date: date | None = None, to_date: date | None = None, include_cancelled: bool = True,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[RetailInvoice], int]:
        q = select(RetailInvoice).where(RetailInvoice.company_id == company_id).options(selectinload(RetailInvoice.customer))
        if search:
            like = f"%{search.strip()}%"
            q = q.outerjoin(RetailCustomer, RetailCustomer.id == RetailInvoice.customer_id).where(or_(
                RetailInvoice.invoice_number.ilike(like), RetailCustomer.name.ilike(like), RetailCustomer.mobile.like(like),
            ))
        if payment_mode:
            q = q.where(RetailInvoice.payment_mode == payment_mode)
        if payment_status:
            q = q.where(RetailInvoice.payment_status == payment_status, RetailInvoice.status == "active")
        if customer_id:
            q = q.where(RetailInvoice.customer_id == customer_id)
        if from_date:
            q = q.where(RetailInvoice.invoice_date >= from_date)
        if to_date:
            q = q.where(RetailInvoice.invoice_date <= to_date)
        if not include_cancelled:
            q = q.where(RetailInvoice.status == "active")
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        rows = (await self.db.execute(
            q.order_by(RetailInvoice.invoice_date.desc(), RetailInvoice.invoice_number.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return rows, total

    async def create_invoice(
        self, body: RetailInvoiceCreate, company_id: UUID, user_id: UUID, can_approve: bool,
    ) -> RetailInvoice:
        if body.client_ref:
            existing = (await self.db.execute(
                select(RetailInvoice.id).where(RetailInvoice.company_id == company_id, RetailInvoice.client_ref == body.client_ref)
            )).scalar_one_or_none()
            if existing:   # the same bill submitted twice — hand back the first one
                return await self.get_invoice(existing, company_id)
        customer = None
        if body.customer_id:
            customer = await self.get_customer(body.customer_id, company_id)
            if not customer:
                raise BusinessRulesError("NOT_FOUND", "Customer not found")
        if body.payment_mode == "credit" and not customer:
            raise BusinessRulesError("CUSTOMER_REQUIRED", "A credit bill needs a registered customer.")
        settings = await self.get_settings(company_id)
        if not settings.warehouse_id:
            raise BusinessRulesError("NO_WAREHOUSE", "Set the retail stock warehouse in Retail Settings first.")

        lines, totals = await self._price(body.items, body.bill_discount_pct, company_id, user_id, can_approve)
        total = totals["total_amount"]
        paid_now = total if body.payment_mode == "cash" else _q(body.amount_paid_now or Decimal("0"))
        if paid_now > total:
            raise BusinessRulesError("OVERPAID", "Amount paid can't be more than the bill total.")
        today = body.invoice_date or date.today()
        now = datetime.now(timezone.utc)
        number = await self._next_number(RetailInvoice, RetailInvoice.invoice_number, "RI", company_id)
        invoice = RetailInvoice(
            company_id=company_id, invoice_number=number, client_ref=body.client_ref,
            customer_id=customer.id if customer else None, invoice_date=today,
            warehouse_id=settings.warehouse_id, payment_mode=body.payment_mode,
            payment_status=_payment_status(total, paid_now), amount_paid=paid_now,
            due_date=today + timedelta(days=settings.credit_days) if body.payment_mode == "credit" else None,
            status="active", estimate_id=body.estimate_id, notes=body.notes,
            created_by=user_id, created_at=now, **totals,
        )
        self.db.add(invoice)
        await self.db.flush()

        for line in lines:
            if line["variant_id"] is None:
                # Unsized stock only — not the product's per-size stock.
                unsized = (await self.db.execute(text("""
                    SELECT COALESCE(SUM(quantity * direction), 0) FROM inventory_transactions
                    WHERE company_id = :cid AND product_id = :pid AND warehouse_id = :wh AND variant_id IS NULL
                """), {"cid": str(company_id), "pid": str(line["product_id"]), "wh": str(settings.warehouse_id)})).scalar()
                if Decimal(unsized) < line["quantity"]:
                    raise BusinessRulesError(
                        "INSUFFICIENT_STOCK",
                        f"Only {Decimal(unsized).normalize():f} of {line['description']} in stock (without a size).",
                        available=Decimal(unsized), shortage=line["quantity"] - Decimal(unsized),
                    )
            cost = await self.inv.get_weighted_avg_cost(company_id, line["product_id"], settings.warehouse_id, line["variant_id"])
            unit_id = line.pop("unit_id")
            if not unit_id:
                raise BusinessRulesError("NO_UNIT", f"{line['description']} has no unit set in the product master")
            txn = await self.inv.issue(IssueParams(
                company_id=company_id, product_id=line["product_id"], variant_id=line["variant_id"],
                warehouse_id=settings.warehouse_id, quantity=line["quantity"], unit_id=unit_id,
                unit_cost=cost, material_type="finished_good", transaction_date=today,
                reference_type="retail_invoice", reference_id=invoice.id, notes=f"Retail bill {number}",
            ), user_id=user_id)
            self.db.add(RetailInvoiceItem(
                invoice_id=invoice.id, unit_id=unit_id, unit_cost=cost, inv_transaction_id=txn.id, **line,
            ))
        if paid_now > 0:
            self.db.add(RetailPayment(
                company_id=company_id, invoice_id=invoice.id, payment_date=today, amount=paid_now,
                mode=body.collection_mode, status="active", created_by=user_id, created_at=now,
                receipt_number=await self._next_number(RetailPayment, RetailPayment.receipt_number, "RR", company_id),
            ))
        await self.db.flush()
        return await self.get_invoice(invoice.id, company_id)

    async def record_payment(
        self, invoice_id: UUID, body: RetailPaymentCreate, company_id: UUID, user_id: UUID,
    ) -> RetailInvoice | None:
        invoice = await self.get_invoice(invoice_id, company_id)
        if not invoice:
            return None
        if body.client_ref and any(p.client_ref == body.client_ref for p in invoice.payments):
            return invoice     # same collection submitted twice
        if invoice.status != "active":
            raise BusinessRulesError("CANCELLED", "This bill is cancelled.")
        outstanding = invoice.total_amount - invoice.amount_paid
        amount = _q(body.amount)
        if outstanding <= 0:
            raise BusinessRulesError("ALREADY_PAID", "This bill is already fully paid.")
        if amount > outstanding:
            raise BusinessRulesError("OVERPAID", f"Only ₹{outstanding} is outstanding on this bill.")
        self.db.add(RetailPayment(
            company_id=company_id, invoice_id=invoice.id, client_ref=body.client_ref,
            payment_date=body.payment_date or date.today(), amount=amount, mode=body.mode,
            reference=body.reference, status="active", created_by=user_id, created_at=datetime.now(timezone.utc),
            receipt_number=await self._next_number(RetailPayment, RetailPayment.receipt_number, "RR", company_id),
        ))
        invoice.amount_paid = invoice.amount_paid + amount
        invoice.payment_status = _payment_status(invoice.total_amount, invoice.amount_paid)
        await self.db.flush()
        self.db.expire(invoice)
        return await self.get_invoice(invoice_id, company_id)

    async def cancel_invoice(self, invoice_id: UUID, reason: str, company_id: UUID, user_id: UUID) -> RetailInvoice | None:
        """Cancel a bill: its stock goes back into the warehouse at the cost it
        left at, and its payments are marked cancelled (refunded)."""
        invoice = await self.get_invoice(invoice_id, company_id)
        if not invoice:
            return None
        if invoice.status == "cancelled":
            raise BusinessRulesError("CANCELLED", "This bill is already cancelled.")
        today = date.today()
        for item in invoice.items:
            await self.inv.receive(ReceiveParams(
                company_id=company_id, product_id=item.product_id, variant_id=item.variant_id,
                warehouse_id=invoice.warehouse_id, quantity=item.quantity, unit_id=item.unit_id,
                unit_cost=item.unit_cost, material_type="finished_good", transaction_date=today,
                reference_type="retail_invoice_cancel", reference_id=invoice.id,
                notes=f"Cancelled retail bill {invoice.invoice_number}",
            ), user_id=user_id)
        for p in invoice.payments:
            p.status = "cancelled"
        invoice.status = "cancelled"
        invoice.amount_paid = Decimal("0")
        invoice.cancelled_at = datetime.now(timezone.utc)
        invoice.cancelled_by = user_id
        invoice.cancel_reason = reason.strip()
        if invoice.estimate_id:
            est = await self.db.get(RetailEstimate, invoice.estimate_id)
            if est and est.converted_invoice_id == invoice.id:
                est.status, est.converted_invoice_id = "accepted", None
        await self.db.flush()
        self.db.expire(invoice)
        return await self.get_invoice(invoice_id, company_id)

    # ── Estimates ──────────────────────────────────────────────────────────

    def _estimate_query(self):
        return select(RetailEstimate).options(selectinload(RetailEstimate.items), selectinload(RetailEstimate.customer))

    async def get_estimate(self, estimate_id: UUID, company_id: UUID) -> RetailEstimate | None:
        return (await self.db.execute(
            self._estimate_query().where(RetailEstimate.id == estimate_id, RetailEstimate.company_id == company_id)
        )).scalar_one_or_none()

    @staticmethod
    def estimate_status(e: RetailEstimate) -> str:
        if e.status in ("draft", "sent") and e.valid_until and e.valid_until < date.today():
            return "expired"
        return e.status

    async def list_estimates(
        self, company_id: UUID, search: str | None = None, status: str | None = None,
        customer_id: UUID | None = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[RetailEstimate], int]:
        q = select(RetailEstimate).where(RetailEstimate.company_id == company_id).options(selectinload(RetailEstimate.customer))
        if search:
            like = f"%{search.strip()}%"
            q = q.outerjoin(RetailCustomer, RetailCustomer.id == RetailEstimate.customer_id).where(or_(
                RetailEstimate.estimate_number.ilike(like), RetailCustomer.name.ilike(like), RetailCustomer.mobile.like(like),
            ))
        today = date.today()
        if status == "expired":
            q = q.where(RetailEstimate.status.in_(("draft", "sent")), RetailEstimate.valid_until < today)
        elif status in ("draft", "sent"):
            q = q.where(RetailEstimate.status == status,
                        or_(RetailEstimate.valid_until.is_(None), RetailEstimate.valid_until >= today))
        elif status:
            q = q.where(RetailEstimate.status == status)
        if customer_id:
            q = q.where(RetailEstimate.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        rows = (await self.db.execute(
            q.order_by(RetailEstimate.estimate_date.desc(), RetailEstimate.estimate_number.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return rows, total

    async def save_estimate(
        self, body: RetailEstimateCreate, company_id: UUID, user_id: UUID, can_approve: bool,
        estimate_id: UUID | None = None,
    ) -> RetailEstimate | None:
        """Create an estimate, or replace a draft/sent one's lines."""
        if body.customer_id and not await self.get_customer(body.customer_id, company_id):
            raise BusinessRulesError("NOT_FOUND", "Customer not found")
        lines, totals = await self._price(body.items, body.bill_discount_pct, company_id, user_id, can_approve)
        for line in lines:
            line.pop("unit_id")
        settings = await self.get_settings(company_id)
        now = datetime.now(timezone.utc)
        est_date = body.estimate_date or date.today()
        valid_until = body.valid_until or est_date + timedelta(days=settings.estimate_validity_days)
        if estimate_id:
            est = await self.get_estimate(estimate_id, company_id)
            if not est:
                return None
            if est.status not in ("draft", "sent"):
                raise BusinessRulesError("LOCKED", "Only a draft or sent estimate can be changed.")
            est.items.clear()
            await self.db.flush()
            est.customer_id, est.estimate_date, est.valid_until = body.customer_id, est_date, valid_until
            est.notes, est.updated_at = body.notes, now
            for k, v in totals.items():
                setattr(est, k, v)
        else:
            est = RetailEstimate(
                company_id=company_id, customer_id=body.customer_id, estimate_date=est_date,
                valid_until=valid_until, status="draft", notes=body.notes, created_by=user_id, created_at=now,
                estimate_number=await self._next_number(RetailEstimate, RetailEstimate.estimate_number, "RE", company_id),
                **totals,
            )
            self.db.add(est)
            await self.db.flush()
        est_id = est.id
        for line in lines:
            self.db.add(RetailEstimateItem(estimate_id=est_id, **line))
        await self.db.flush()
        self.db.expire(est)
        return await self.get_estimate(est_id, company_id)

    async def set_estimate_status(self, estimate_id: UUID, status: str, company_id: UUID) -> RetailEstimate | None:
        est = await self.get_estimate(estimate_id, company_id)
        if not est:
            return None
        if est.status == "converted":
            raise BusinessRulesError("LOCKED", "This estimate has already been billed.")
        est.status = status
        est.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return est

    async def convert_estimate(
        self, estimate_id: UUID, body: RetailEstimateConvert, company_id: UUID, user_id: UUID, can_approve: bool,
    ) -> RetailInvoice | None:
        est = await self.get_estimate(estimate_id, company_id)
        if not est:
            return None
        if est.status == "converted":
            raise BusinessRulesError("LOCKED", "This estimate has already been billed.")
        if self.estimate_status(est) == "expired":
            raise BusinessRulesError("EXPIRED", "This estimate has expired — extend its validity or make a new one.")
        if est.status == "rejected":
            raise BusinessRulesError("LOCKED", "This estimate was rejected.")
        invoice = await self.create_invoice(RetailInvoiceCreate(
            client_ref=body.client_ref, customer_id=est.customer_id, payment_mode=body.payment_mode,
            amount_paid_now=body.amount_paid_now, collection_mode=body.collection_mode,
            bill_discount_pct=est.bill_discount_pct, notes=est.notes, estimate_id=est.id,
            items=[RetailLineIn(
                product_id=i.product_id, variant_id=i.variant_id, quantity=i.quantity,
                item_discount_pct=i.item_discount_pct, unit_price=i.unit_price,
            ) for i in est.items],
        ), company_id, user_id, can_approve)
        est.status, est.converted_invoice_id = "converted", invoice.id
        est.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return invoice
