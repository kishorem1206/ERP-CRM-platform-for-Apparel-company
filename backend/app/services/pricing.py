from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PriceResult:
    unit_price: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    source: str  # e.g. "customer_price_list", "price_list", "wholesale", "mrp", "not_found"


@dataclass
class TaxBreakdown:
    taxable_value: Decimal
    gst_rate: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal


@dataclass
class CostSheet:
    raw_material_cost: Decimal
    cost_after_wastage: Decimal
    total_cost: Decimal          # after wastage + overhead
    wastage_pct: Decimal
    wastage_amount: Decimal
    overhead_pct: Decimal
    overhead_amount: Decimal
    margin_pct: Decimal
    selling_price: Decimal
    breakdown: list[dict]


def _round(value: Decimal, places: int = 2) -> Decimal:
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def _item_valid_on(item, list_valid_from: date | None, list_valid_to: date | None, on_date: date) -> bool:
    """Item-level valid_from/valid_to wins when set; otherwise falls back to
    the parent price list's window. No window at all means always valid."""
    start = item.valid_from or list_valid_from
    end = item.valid_to or list_valid_to
    if start and on_date < start:
        return False
    if end and on_date > end:
        return False
    return True


class PricingService:
    """
    Deterministic pricing engine. Never delegates calculations to LLM.
    All arithmetic uses Decimal to avoid float imprecision.
    db is optional — pure calculation methods work without it.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def get_price(
        self,
        company_id: UUID,
        product_id: UUID,
        variant_id: UUID | None,
        customer_id: UUID | None,
        quantity: Decimal,
        on_date: date,
    ) -> PriceResult:
        """Resolution order (each step only tried if the previous finds
        nothing): customer-specific price-list override -> generic price
        for the customer's assigned list -> Product/Variant.wholesale_price
        -> Product/Variant.mrp -> not_found. The `source` on the result
        distinguishes an actually-configured price from either fallback, so
        callers never mistake one for the other."""
        if self.db is None:
            raise RuntimeError("get_price requires a database session")

        from app.models.master import Product, ProductVariant
        from app.models.sales import Customer, PriceList, PriceListItem

        price_list_id: UUID | None = None
        if customer_id:
            cust_result = await self.db.execute(
                select(Customer.price_list_id).where(Customer.id == customer_id, Customer.company_id == company_id)
            )
            price_list_id = cust_result.scalar_one_or_none()

        if price_list_id:
            qty_filters = [
                PriceListItem.price_list_id == price_list_id,
                PriceListItem.product_id == product_id,
                or_(PriceListItem.variant_id == variant_id, PriceListItem.variant_id.is_(None)) if variant_id
                else PriceListItem.variant_id.is_(None),
                PriceListItem.min_quantity <= quantity,
                or_(PriceListItem.max_quantity.is_(None), PriceListItem.max_quantity >= quantity),
            ]

            async def _best_match(customer_scoped: bool):
                scope = PriceListItem.customer_id == customer_id if customer_scoped else PriceListItem.customer_id.is_(None)
                res = await self.db.execute(
                    select(PriceListItem, PriceList.valid_from, PriceList.valid_to)
                    .join(PriceList, PriceList.id == PriceListItem.price_list_id)
                    .where(*qty_filters, scope)
                )
                for item, list_from, list_to in res.all():
                    if _item_valid_on(item, list_from, list_to, on_date):
                        return item
                return None

            item = await _best_match(customer_scoped=True) if customer_id else None
            source = "customer_price_list"
            if not item:
                item = await _best_match(customer_scoped=False)
                source = "price_list"

            if item:
                unit_price = Decimal(str(item.unit_price))
                discount_pct = Decimal(str(item.discount_pct or 0))
                discount_amount = _round(unit_price * quantity * discount_pct / 100)
                taxable = _round(unit_price * quantity - discount_amount)
                return PriceResult(
                    unit_price=unit_price, discount_pct=discount_pct,
                    discount_amount=discount_amount, taxable_amount=taxable, source=source,
                )

        result = await self.db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        variant = None
        if variant_id:
            variant_result = await self.db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
            variant = variant_result.scalar_one_or_none()

        wholesale_price = (variant.wholesale_price if variant else None) or (product.wholesale_price if product else None)
        if wholesale_price:
            unit_price = Decimal(str(wholesale_price))
            taxable = _round(unit_price * quantity)
            return PriceResult(
                unit_price=unit_price,
                discount_pct=Decimal("0"),
                discount_amount=Decimal("0"),
                taxable_amount=taxable,
                source="wholesale",
            )

        mrp = (variant.mrp if variant else None) or (product.mrp if product else None)
        if mrp:
            unit_price = Decimal(str(mrp))
            taxable = _round(unit_price * quantity)
            return PriceResult(
                unit_price=unit_price,
                discount_pct=Decimal("0"),
                discount_amount=Decimal("0"),
                taxable_amount=taxable,
                source="mrp",
            )

        return PriceResult(
            unit_price=Decimal("0"),
            discount_pct=Decimal("0"),
            discount_amount=Decimal("0"),
            taxable_amount=Decimal("0"),
            source="not_found",
        )

    def calculate_cost_sheet(
        self,
        components: list[dict],
        wastage_pct: Decimal = Decimal("0"),
        overhead_pct: Decimal = Decimal("0"),
        margin_pct: Decimal = Decimal("20"),
    ) -> CostSheet:
        """
        components: list of {"name": str, "qty": Decimal, "unit_cost": Decimal}
        """
        raw_material_cost = _round(
            sum(Decimal(str(c["qty"])) * Decimal(str(c["unit_cost"])) for c in components)
        )

        wastage_amount = _round(raw_material_cost * wastage_pct / 100)
        cost_after_wastage = _round(raw_material_cost + wastage_amount)

        overhead_amount = _round(cost_after_wastage * overhead_pct / 100)
        total_cost = _round(cost_after_wastage + overhead_amount)

        if margin_pct >= 100:
            selling_price = total_cost
        else:
            selling_price = _round(total_cost / (1 - margin_pct / 100))

        breakdown = [
            {"name": c["name"], "qty": float(c["qty"]), "unit_cost": float(c["unit_cost"]),
             "amount": float(Decimal(str(c["qty"])) * Decimal(str(c["unit_cost"])))}
            for c in components
        ]
        breakdown.append({"name": "Wastage", "amount": float(wastage_amount)})
        breakdown.append({"name": "Overhead", "amount": float(overhead_amount)})

        return CostSheet(
            raw_material_cost=raw_material_cost,
            cost_after_wastage=cost_after_wastage,
            total_cost=total_cost,
            wastage_pct=wastage_pct,
            wastage_amount=wastage_amount,
            overhead_pct=overhead_pct,
            overhead_amount=overhead_amount,
            margin_pct=margin_pct,
            selling_price=selling_price,
            breakdown=breakdown,
        )


class TaxService:
    """
    Deterministic GST calculation. Never delegates to LLM.
    db is optional — sync helper methods work without it.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    def is_intrastate(self, supplier_state_code: str, customer_state_code: str) -> bool:
        return supplier_state_code == customer_state_code

    def split_rate(
        self, gst_rate: Decimal, intrastate: bool
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (cgst_rate, sgst_rate, igst_rate)."""
        if intrastate:
            half = _round(gst_rate / 2)
            return half, half, Decimal("0")
        return Decimal("0"), Decimal("0"), gst_rate

    async def determine_tax(
        self,
        product_id: UUID,
        customer_state_code: int,
        company_state_code: int,
        taxable_value: Decimal,
        transaction_date: date,
    ) -> TaxBreakdown:
        if self.db is None:
            raise RuntimeError("determine_tax requires a database session")

        from app.models.master import Product, HsnCode

        result = await self.db.execute(
            select(HsnCode)
            .join(Product, Product.hsn_id == HsnCode.id)
            .where(Product.id == product_id)
        )
        hsn = result.scalar_one_or_none()
        gst_rate = Decimal(str(hsn.gst_rate)) if hsn else Decimal("5")
        cess_rate = Decimal(str(hsn.cess_rate)) if hsn else Decimal("0")

        intrastate = self.is_intrastate(str(company_state_code), str(customer_state_code))
        cgst_rate, sgst_rate, igst_rate = self.split_rate(gst_rate, intrastate)

        cgst_amount = _round(taxable_value * cgst_rate / 100)
        sgst_amount = _round(taxable_value * sgst_rate / 100)
        igst_amount = _round(taxable_value * igst_rate / 100)
        cess_amount = _round(taxable_value * cess_rate / 100)
        total_tax = cgst_amount + sgst_amount + igst_amount + cess_amount

        return TaxBreakdown(
            taxable_value=taxable_value,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            cess_amount=cess_amount,
            total_tax=total_tax,
            grand_total=_round(taxable_value + total_tax),
        )
