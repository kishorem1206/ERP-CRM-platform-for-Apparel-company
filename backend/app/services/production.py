"""ProductionService: lots, stages, MIS, stage entries, FG output."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.business_rules import BusinessRulesError, business_rules
from app.models.master import Product, ProductVariant
from app.models.production import (
    FabricProcessingEntry, InternalWorker, LotAdditionalCost, LotFabric, LotPackingMaterial, LotPartColour, LotPartSize,
    LotTrim, LotYarn, MaterialIssue, MaterialIssueItem, ProductionMistakeLog,
    ProcessMaster, ProductionAuditLog, ProductionLot, ProductionLotSize, ProductionOutput,
    ProductionStage, ProductionStageChallan, ProductionStageEntry, ProductionStageSize, SizeChart, SizeChartItem, Style, StyleAdditionalCost,
    StyleColour, StyleFabric, StyleFabricSize, StylePackingMaterial, StylePart, StylePartColour, StylePartSize, StyleProcess,
    StyleSize, StyleSubProcess, StyleTrim, StyleTrimSize, StyleYarn,
)
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.inventory import IssueParams, ReceiveParams
from app.schemas.production import (
    FabricProcessingComplete, FabricProcessingCreate, FabricProcessingUpdate,
    InternalWorkerCreate,
    LotAdditionalCostCreate, LotAdditionalCostUpdate, LotCostComponentOut, LotCostSummaryOut,
    LotFabricActualUpdate, LotYarnActualUpdate,
    LotPackingActualUpdate, LotTrimActualUpdate,
    MaterialIssueCreate, MISItemCreate, MISItemReturnUpdate, MistakeLogCreate,
    ProductionLotCreate, ProductionLotUpdate,
    ProductionOutputCreate, SizeChartCreate, StyleSizeIn,
    StageChallanBillUpdate, StageChallanCreate, StageChallanReceive,
    StageCreate, StageEntryCreate, StageSizeUpdate, StageUpdate, StyleCreate, StyleProcessIn,
    TargetPriceCheckOut, TargetPriceSuggestion,
)
from app.services.inventory import InventoryService
from app.services.sku import build_variant_sku


# Everything the API's _stage_out() reads off a ProductionStage. Any query
# whose result is serialized through _stage_out must load all of these, or
# Pydantic's sync validation hits an unloaded async relationship and raises
# MissingGreenlet.
_STAGE_OUT_LOADS = (
    selectinload(ProductionStage.entries),
    selectinload(ProductionStage.challans),
    selectinload(ProductionStage.sizes),
    selectinload(ProductionStage.style_process).selectinload(StyleProcess.sub_processes),
)


# Everything the API's _lot_out() (and compute_lot_cost_summary, build_lot_bom,
# fabric_blockers) reads off a ProductionLot. get_lot, list_lots and
# create_lot's final re-fetch all use this one set; when they each kept their
# own copy, list_lots and create_lot drifted behind get_lot and both crashed
# with MissingGreenlet as soon as _stage_out started reading stage.sizes and
# stage.style_process.sub_processes.
_LOT_FULL_LOADS = (
    selectinload(ProductionLot.style).selectinload(Style.fabrics),
    selectinload(ProductionLot.style).selectinload(Style.trims),
    selectinload(ProductionLot.style).selectinload(Style.yarns),
    selectinload(ProductionLot.sizes),
    selectinload(ProductionLot.part_colours).selectinload(LotPartColour.style_part),
    selectinload(ProductionLot.part_colours).selectinload(LotPartColour.colour),
    selectinload(ProductionLot.part_colours).selectinload(LotPartColour.sizes),
    selectinload(ProductionLot.stages).selectinload(ProductionStage.entries),
    selectinload(ProductionLot.stages).selectinload(ProductionStage.challans),
    selectinload(ProductionLot.stages).selectinload(ProductionStage.style_process).selectinload(StyleProcess.sub_processes),
    selectinload(ProductionLot.stages).selectinload(ProductionStage.sizes),
    selectinload(ProductionLot.additional_costs),
    selectinload(ProductionLot.trims),
    selectinload(ProductionLot.packing_materials).selectinload(LotPackingMaterial.product),
    selectinload(ProductionLot.lot_fabrics).selectinload(LotFabric.style_part),
    selectinload(ProductionLot.lot_fabrics).selectinload(LotFabric.colour),
    selectinload(ProductionLot.lot_fabrics).selectinload(LotFabric.yarns),
    selectinload(ProductionLot.lot_yarns).selectinload(LotYarn.colour),
    selectinload(ProductionLot.fabric_processing),
    selectinload(ProductionLot.material_issues).selectinload(MaterialIssue.items),
    selectinload(ProductionLot.outputs),
)


def _stage_accepted_qty(stage: ProductionStage) -> int:
    """The stage's actual accepted output — what flows to the next stage's
    planned_qty. Outsourced stages (vendor/internal_worker) use the job-work
    challan rollup (received_qty); in-house stages use the manual entry
    rollup (output_qty).
    """
    return stage.received_qty if stage.assignment_type else stage.output_qty


def _stage_has_activity(stage: ProductionStage) -> bool:
    return stage.sent_qty > 0 or stage.input_qty > 0


def _stage_actual_cost(stage: ProductionStage) -> Decimal:
    """Actual cost for a stage: rate_per_pc × accepted qty when a rate is
    configured (the agreed per-piece rate is the authoritative billing basis),
    else the sum of the stage's challan bill amounts as a fallback for stages
    billed purely off an invoice with no per-piece rate on file — never both
    summed together, which would double-count the same work.
    """
    if stage.rate_per_pc is not None:
        return (stage.rate_per_pc * _stage_accepted_qty(stage)).quantize(Decimal("0.01"))
    return sum((c.bill_amount or Decimal("0") for c in stage.challans), Decimal("0"))


class QuantityValidationError(ValueError):
    """Raised when a production quantity movement would violate OUT ≤ IN
    (Garments_ERP_Style_Master_Specification.md §47.6) — endpoints translate this
    to HTTP 422.
    """


async def _next_seq(db: AsyncSession, prefix: str, company_id: UUID, model_cls) -> str:
    """Non-safe fallback used only for MIS/OUT sequences until document_sequences covers them."""
    result = await db.execute(select(func.count()).where(model_cls.company_id == company_id))
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:05d}"


def compute_target_price_check(style: Style) -> TargetPriceCheckOut | None:
    """Deterministic Target Price guidance (§47.18): compare the sum of a Style's
    configured process planned rates against its target price, and — if over
    budget — suggest which stage(s) to reduce, and by how much, to close the gap.

    Pure function of already-loaded data (style.target_price / style.processes) —
    not persisted, so it always reflects the Style's *current* configuration rather
    than a frozen LOT snapshot.
    """
    if style.target_price is None:
        return None
    enabled = [p for p in style.processes if p.is_enabled and p.planned_rate is not None]
    if not enabled:
        return None

    planned_process_cost = sum((p.planned_rate for p in enabled), Decimal("0"))
    target_price = style.target_price
    gap = planned_process_cost - target_price

    suggestions: list[TargetPriceSuggestion] = []
    if gap > 0:
        remaining = gap
        for p in sorted(enabled, key=lambda p: p.planned_rate, reverse=True):
            if remaining <= 0:
                break
            reduction = min(p.planned_rate, remaining)
            suggestions.append(TargetPriceSuggestion(
                process_name=p.process_name, current_rate=p.planned_rate,
                suggested_rate=(p.planned_rate - reduction).quantize(Decimal("0.01")),
                delta=(-reduction).quantize(Decimal("0.01")),
            ))
            remaining -= reduction
        message = (
            f"Over target by ₹{gap.quantize(Decimal('0.01'))} — reduce the rates below to meet ₹{target_price}."
        )
    else:
        message = (
            f"₹{(-gap).quantize(Decimal('0.01'))} of cushion below your target price — "
            "no rate changes needed; this is how much you could raise rates and still meet it."
        )

    return TargetPriceCheckOut(
        planned_process_cost=planned_process_cost.quantize(Decimal("0.01")),
        target_price=target_price, gap=gap.quantize(Decimal("0.01")),
        message=message, suggestions=suggestions,
    )


# Default general wastage tolerance (§47.16) — used only when the Style has no
# single unambiguous fabric-row excess_pct to use instead.
DEFAULT_WASTAGE_PCT = Decimal("3")

_CENTS = Decimal("0.01")


def _cost_component(
    name: str, planned: Decimal | None, actual: Decimal | None, note: str | None = None,
) -> LotCostComponentOut:
    variance_amount = None
    variance_pct = None
    if planned is not None and actual is not None:
        variance_amount = (actual - planned).quantize(_CENTS)
        if planned != 0:
            variance_pct = (variance_amount / planned * 100).quantize(_CENTS)
    return LotCostComponentOut(
        name=name, planned_amount=planned, actual_amount=actual,
        variance_amount=variance_amount, variance_pct=variance_pct, note=note,
    )


def compute_lot_cost_summary(
    lot: ProductionLot, selling_prices: dict[UUID, tuple[Decimal, str]] | None = None,
) -> LotCostSummaryOut:
    """Deterministic LOT cost + profitability aggregation: Material, Wastage,
    Fabric Processing, one row per actual production stage (dynamic — never
    hard-coded to a fixed stage list), Additional Costs, and Agent Commission
    — each independently sourced from data already captured, never fabricated.
    Also derives actual cost/selling-price/profit/margin per saleable piece.

    `selling_prices` is a pre-resolved {product_id: (price, source_label)} map
    (see ProductionService.resolve_selling_prices) — this function stays a
    pure computation with no DB access of its own.

    Requires `lot.stages` (with `.challans`), `lot.fabric_processing`,
    `lot.additional_costs`, `lot.material_issues` (with `.items`), and
    `lot.outputs` eager-loaded.
    """
    warnings: list[str] = []
    selling_prices = selling_prices or {}

    material_cost = sum(
        (item.total_cost for mis in lot.material_issues for item in mis.items),
        Decimal("0"),
    )

    wastage_pct = DEFAULT_WASTAGE_PCT
    fabrics = lot.style.fabrics if lot.style else []
    fabrics_with_excess = [f for f in fabrics if f.excess_pct is not None]
    if len(fabrics) == 1 and fabrics_with_excess:
        wastage_pct = fabrics_with_excess[0].excess_pct
    wastage_amount = (material_cost * wastage_pct / 100).quantize(_CENTS)

    fabric_processing_cost = Decimal("0")
    for f in lot.fabric_processing:
        if f.status == "completed" and f.bill_amount is None:
            warnings.append(f"Fabric processing ({f.process_type}, {f.in_date}) has no bill amount set.")
        fabric_processing_cost += f.bill_amount or Decimal("0")

    # One component row per actual production stage, in lot order — dynamic,
    # not bucketed into a fixed cutting/making/other grouping, so any
    # configured process (Checking, Ironing, Trimming, Fusing, Printing,
    # Embroidery, Washing, ...) shows up under its own real name.
    process_components: list[LotCostComponentOut] = []
    process_actual_total = Decimal("0")
    planned_process_total = Decimal("0")
    for s in lot.stages:
        if _stage_has_activity(s) and s.rate_per_pc is None and not any(c.bill_amount for c in s.challans):
            warnings.append(f"Stage '{s.stage_name}' has activity but no rate or bill set.")
        for c in s.challans:
            if c.status in ("received", "partial") and c.bill_amount is None:
                warnings.append(f"Challan {c.challan_number} ({s.stage_name}) has no bill amount set.")
        actual = _stage_actual_cost(s)
        planned = (s.planned_rate * lot.planned_qty).quantize(_CENTS) if s.planned_rate is not None else None
        process_actual_total += actual
        planned_process_total += planned or Decimal("0")
        accepted = _stage_accepted_qty(s)
        note = None
        if accepted > 0:
            via = {"vendor": " via vendor", "internal_worker": " via internal worker"}.get(s.assignment_type or "", "")
            note = f"{accepted} pcs accepted{via}"
        process_components.append(_cost_component(s.stage_name, planned, actual, note))

    additional_cost = sum(
        (a.actual_amount or Decimal("0") for a in lot.additional_costs if a.cost_type == "additional"),
        Decimal("0"),
    )
    agent_commission = sum(
        (a.actual_amount or Decimal("0") for a in lot.additional_costs if a.cost_type == "agent_commission"),
        Decimal("0"),
    )
    planned_additional_total = sum(
        (a.planned_amount or Decimal("0") for a in lot.additional_costs if a.cost_type == "additional"),
        Decimal("0"),
    )
    planned_agent_commission_total = sum(
        (a.planned_amount or Decimal("0") for a in lot.additional_costs if a.cost_type == "agent_commission"),
        Decimal("0"),
    )

    components = [
        _cost_component(
            "Material Cost (Fabric & Trims)", None, material_cost,
            "Planned material cost not available — Style Fabric/Trim track consumption and excess %, not a configured unit cost.",
        ),
        _cost_component(
            "Wastage / Tolerance", None, wastage_amount,
            f"{wastage_pct}% applied" + ("" if fabrics_with_excess and len(fabrics) == 1 else f" (default — {DEFAULT_WASTAGE_PCT}% general tolerance)"),
        ),
        _cost_component("Fabric Processing", None, fabric_processing_cost),
        *process_components,
        _cost_component("Additional Costs", planned_additional_total, additional_cost),
        _cost_component("Agent Commission", planned_agent_commission_total or None, agent_commission),
    ]

    total_actual = (
        material_cost + wastage_amount + fabric_processing_cost
        + process_actual_total + additional_cost + agent_commission
    ).quantize(_CENTS)
    total_planned = (planned_process_total + planned_additional_total + planned_agent_commission_total).quantize(_CENTS)

    # Rejected pieces are lost at two different checkpoints — in-process,
    # stage by stage (e.g. Stitching/Checking/Ironing rejecting some of what
    # they receive), and at final goods receipt (ProductionOutput.rejected_qty,
    # first-quality vs rejected at FG receive). Both must count: a lot can
    # lose all 10 of its rejects mid-process and pass every FG receipt
    # cleanly, in which case the FG-only figure would show 0 rejected even
    # though 10 pieces never became saleable.
    first_quality_qty = sum((o.quantity for o in lot.outputs), Decimal("0"))
    fg_rejected_qty = sum((o.rejected_qty or Decimal("0") for o in lot.outputs), Decimal("0"))
    stage_rejected_qty = Decimal(sum((s.rejected_qty for s in lot.stages), 0))
    rejected_qty = fg_rejected_qty + stage_rejected_qty
    total_output_qty = first_quality_qty + rejected_qty
    yield_pct = (first_quality_qty / total_output_qty * 100).quantize(_CENTS) if total_output_qty > 0 else None
    cost_per_piece = (total_actual / first_quality_qty).quantize(_CENTS) if first_quality_qty > 0 else None

    target_price = lot.target_sp
    target_revenue = (target_price * lot.planned_qty).quantize(_CENTS) if target_price is not None else None
    expected_margin_pct = None
    if target_revenue is not None and target_revenue > 0:
        expected_margin_pct = ((target_revenue - total_planned) / target_revenue * 100).quantize(_CENTS)

    # Actual selling price / revenue / profit / margin. Highest priority: the
    # lot's own actual_selling_price, set manually once real sale terms are
    # known (a single number covering all output — the user is stating "this
    # is what we actually sold it for", not asking us to resolve it product
    # by product). Otherwise, resolved per distinct product actually produced
    # (a lot can output more than one FG product) via `selling_prices`
    # (sales-order item, else product MRP), weighted by saleable quantity.
    actual_selling_price_per_piece = None
    selling_price_source = None
    actual_revenue = None
    profit_per_piece = None
    actual_profit = None
    gross_margin_pct = None

    if first_quality_qty > 0 and lot.actual_selling_price is not None:
        actual_selling_price_per_piece = lot.actual_selling_price
        selling_price_source = "Set on lot"
        actual_revenue = (lot.actual_selling_price * first_quality_qty).quantize(_CENTS)
    elif first_quality_qty > 0:
        qty_by_product: dict[UUID, Decimal] = {}
        for o in lot.outputs:
            qty_by_product[o.product_id] = qty_by_product.get(o.product_id, Decimal("0")) + o.quantity
        revenue_total = Decimal("0")
        resolved_qty = Decimal("0")
        sources: set[str] = set()
        unresolved = 0
        for pid, qty in qty_by_product.items():
            price_info = selling_prices.get(pid)
            if price_info is None:
                unresolved += 1
                continue
            price, source = price_info
            revenue_total += qty * price
            resolved_qty += qty
            sources.add(source)
        if unresolved:
            warnings.append(
                f"Selling price not configured for {unresolved} product(s) produced on this lot — "
                "actual revenue/profit/margin exclude them."
            )
        if resolved_qty > 0:
            actual_revenue = revenue_total.quantize(_CENTS)
            actual_selling_price_per_piece = (actual_revenue / resolved_qty).quantize(_CENTS)
            selling_price_source = sources.pop() if len(sources) == 1 else (
                f"{len(sources)} sources" if sources else None
            )

    if actual_selling_price_per_piece is not None and cost_per_piece is not None:
        profit_per_piece = (actual_selling_price_per_piece - cost_per_piece).quantize(_CENTS)
        if actual_revenue is not None:
            actual_profit = (actual_revenue - total_actual).quantize(_CENTS)
        if actual_selling_price_per_piece > 0:
            gross_margin_pct = (
                (actual_selling_price_per_piece - cost_per_piece) / actual_selling_price_per_piece * 100
            ).quantize(_CENTS)

    is_final = lot.status in ("completed", "packing")

    return LotCostSummaryOut(
        components=components,
        total_planned=total_planned,
        total_actual=total_actual,
        first_quality_qty=first_quality_qty,
        rejected_qty=rejected_qty,
        total_output_qty=total_output_qty,
        yield_pct=yield_pct,
        cost_per_first_quality_piece=cost_per_piece,
        target_price=target_price,
        target_revenue=target_revenue,
        expected_margin_pct=expected_margin_pct,
        actual_selling_price_per_piece=actual_selling_price_per_piece,
        selling_price_source=selling_price_source,
        actual_revenue=actual_revenue,
        profit_per_piece=profit_per_piece,
        actual_profit=actual_profit,
        gross_margin_pct=gross_margin_pct,
        is_final=is_final,
        missing_rate_warnings=warnings,
    )


class ProductionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    async def resolve_selling_prices(self, lot: ProductionLot) -> dict[UUID, tuple[Decimal, str]]:
        """Actual selling price per FG product this lot produced, highest
        priority first: (1) the real order price, when this lot is linked to
        a sales order and that order prices the product; (2) the product's
        configured MRP. Products the lot didn't actually output aren't
        resolved. Pure DB reads — used to feed compute_lot_cost_summary(),
        which stays a pure computation with no I/O of its own.
        """
        product_ids = {o.product_id for o in lot.outputs}
        if not product_ids:
            return {}

        resolved: dict[UUID, tuple[Decimal, str]] = {}

        if lot.sales_order_id:
            result = await self.db.execute(
                select(SalesOrderItem, SalesOrder.order_number)
                .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
                .where(SalesOrderItem.sales_order_id == lot.sales_order_id, SalesOrderItem.product_id.in_(product_ids))
            )
            for item, order_number in result.all():
                resolved[item.product_id] = (item.unit_price, f"Sales Order {order_number}")

        remaining = product_ids - resolved.keys()
        if remaining:
            result = await self.db.execute(
                select(Product).where(Product.id.in_(remaining), Product.mrp.is_not(None))
            )
            for product in result.scalars().all():
                resolved[product.id] = (product.mrp, "Product MRP")

        return resolved

    async def _next_lot_number(self, company_id: UUID) -> str:
        """Concurrency-safe lot number from document_sequences (SELECT FOR UPDATE)."""
        result = await self.db.execute(
            text("""
                SELECT prefix, separator, year_format, next_number, padding
                FROM document_sequences
                WHERE company_id = :cid AND document_type = 'production_lot'
                FOR UPDATE
            """),
            {"cid": str(company_id)},
        )
        row = result.mappings().first()
        if row is None:
            # Fallback if sequence row is missing
            count = (await self.db.execute(
                select(func.count()).where(ProductionLot.company_id == company_id)
            )).scalar() or 0
            return f"LOT{count + 1:05d}"

        prefix = row["prefix"] or "LOT"
        sep = row["separator"] or ""
        next_num = row["next_number"]
        padding = row["padding"] or 5
        year_format = row["year_format"] or ""

        year_part = ""
        if year_format:
            _fmt = {"YY": "%y", "YYYY": "%Y"}.get(year_format, year_format)
            year_part = datetime.now(timezone.utc).strftime(_fmt) + sep

        lot_number = f"{prefix}{sep}{year_part}{str(next_num).zfill(padding)}"

        await self.db.execute(
            text("""
                UPDATE document_sequences SET next_number = next_number + 1
                WHERE company_id = :cid AND document_type = 'production_lot'
            """),
            {"cid": str(company_id)},
        )
        return lot_number

    async def _next_challan_number(self, company_id: UUID) -> str:
        """Concurrency-safe job-work challan number from document_sequences —
        mirrors _next_lot_number()'s SELECT FOR UPDATE / increment shape.
        """
        result = await self.db.execute(
            text("""
                SELECT prefix, separator, year_format, next_number, padding
                FROM document_sequences
                WHERE company_id = :cid AND document_type = 'job_work_challan'
                FOR UPDATE
            """),
            {"cid": str(company_id)},
        )
        row = result.mappings().first()
        if row is None:
            count = (await self.db.execute(
                select(func.count()).select_from(ProductionStageChallan)
                .join(ProductionStage, ProductionStage.id == ProductionStageChallan.production_stage_id)
                .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
                .where(ProductionLot.company_id == company_id)
            )).scalar() or 0
            return f"JWC{count + 1:05d}"

        prefix = row["prefix"] or "JWC"
        sep = row["separator"] or ""
        next_num = row["next_number"]
        padding = row["padding"] or 4
        year_format = row["year_format"] or ""

        year_part = ""
        if year_format:
            _fmt = {"YY": "%y", "YYYY": "%Y"}.get(year_format, year_format)
            year_part = datetime.now(timezone.utc).strftime(_fmt) + sep

        challan_number = f"{prefix}{sep}{year_part}{str(next_num).zfill(padding)}"

        await self.db.execute(
            text("""
                UPDATE document_sequences SET next_number = next_number + 1
                WHERE company_id = :cid AND document_type = 'job_work_challan'
            """),
            {"cid": str(company_id)},
        )
        return challan_number

    # ── Styles ─────────────────────────────────────────────────────────────

    async def list_styles(self, company_id: UUID) -> list[Style]:
        result = await self.db.execute(
            select(Style).where(Style.company_id == company_id).order_by(Style.name)
        )
        return result.scalars().all()

    def _style_detail_query(self):
        return select(Style).options(
            selectinload(Style.product).selectinload(Product.hsn),
            selectinload(Style.brand),
            selectinload(Style.sizes),
            selectinload(Style.colours),
            selectinload(Style.part_colours).selectinload(StylePartColour.style_part),
            selectinload(Style.part_colours).selectinload(StylePartColour.sizes),
            selectinload(Style.yarns).selectinload(StyleYarn.style_fabric),
            selectinload(Style.yarns).selectinload(StyleYarn.colour),
            selectinload(Style.fabrics).selectinload(StyleFabric.size_breakdown),
            selectinload(Style.fabrics).selectinload(StyleFabric.style_part),
            selectinload(Style.processes).selectinload(StyleProcess.sub_processes),
            selectinload(Style.processes).selectinload(StyleProcess.style_part),
            selectinload(Style.trims).selectinload(StyleTrim.size_breakdown),
            selectinload(Style.trims).selectinload(StyleTrim.style_part),
            selectinload(Style.trims).selectinload(StyleTrim.colour),
            selectinload(Style.packing_materials),
            selectinload(Style.additional_costs),
        )

    async def get_style(self, style_id: UUID, company_id: UUID) -> Style | None:
        result = await self.db.execute(
            self._style_detail_query().where(Style.id == style_id, Style.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def _resolve_style_product(
        self, body: StyleCreate, company_id: UUID, user_id: UUID, existing_product_id: UUID | None = None,
    ) -> UUID:
        """Every Style must have a real sellable Product/SKU master behind it
        (Garments_ERP_Style_Master_Specification.md §4-5) rather than Style
        duplicating product identity in free-text fields. If the caller
        points at an existing Product, (re)link it (company-scoped, error
        otherwise); if the Style is already linked and the caller didn't ask
        to change it, keep that link; otherwise auto-create one from the
        Style's own fields so the guarantee holds without an extra manual step.
        """
        if body.product_id:
            result = await self.db.execute(
                select(Product).where(Product.id == body.product_id, Product.company_id == company_id)
            )
            product = result.scalar_one_or_none()
            if not product:
                raise BusinessRulesError("product_not_found", "Linked product not found")
            return product.id

        if existing_product_id:
            return existing_product_id

        product = Product(
            company_id=company_id,
            code=body.code or f"STY-{uuid4().hex[:8].upper()}",
            name=body.name, product_type="finished_good",
            gender=body.gender, season=body.season, brand_id=body.brand_id,
            created_by=user_id,
        )
        self.db.add(product)
        await self.db.flush()
        return product.id

    async def _ensure_variants(self, style: Style) -> None:
        """Turns a Style's size x colour combinations into real ProductVariant
        SKUs under its linked product (§4: "Style + applicable variant
        dimensions = SKU/variant"). Existence-checked so repeated calls (every
        update_style run) never duplicate a variant that already exists.
        """
        if not style.product_id:
            return
        # Query fresh rather than via style.sizes/style.colours: update_style
        # deletes+reinserts those child rows earlier in the same session, and
        # the already-identity-mapped `style` object's relationship
        # collections won't reflect that without an explicit reload.
        size_ids = (await self.db.execute(
            select(StyleSize.size_id).where(StyleSize.style_id == style.id)
        )).scalars().all()
        colour_ids = (await self.db.execute(
            select(StyleColour.colour_id).where(StyleColour.style_id == style.id)
        )).scalars().all()
        sizes = size_ids or [None]
        colours = colour_ids or [None]
        if sizes == [None] and colours == [None]:
            return

        existing = await self.db.execute(
            select(ProductVariant.size_id, ProductVariant.colour_id)
            .where(ProductVariant.product_id == style.product_id)
        )
        existing_pairs = {(row.size_id, row.colour_id) for row in existing}

        product = (await self.db.execute(select(Product).where(Product.id == style.product_id))).scalar_one()
        for size_id in sizes:
            for colour_id in colours:
                if (size_id, colour_id) in existing_pairs:
                    continue
                sku = await build_variant_sku(self.db, product.code, size_id, colour_id)
                self.db.add(ProductVariant(product_id=style.product_id, sku=sku, size_id=size_id, colour_id=colour_id))
                existing_pairs.add((size_id, colour_id))
        await self.db.flush()

    async def _ensure_part_variants(self, style: Style) -> None:
        """Mirrors _ensure_variants, but for Style Parts (Production Module
        Reorganisation Phase 1): one variant per (part, colour, size) a part
        is configured for, in ADDITION to the style's regular whole-garment
        variants — these track the individual part (e.g. "Collar-M-Red"),
        not the assembled product. A style with no parts configured
        generates none of these, so it's a pure no-op for every style that
        existed before this feature.
        """
        if not style.product_id:
            return
        part_colours = (await self.db.execute(
            select(StylePartColour).where(StylePartColour.style_id == style.id)
            .options(selectinload(StylePartColour.sizes))
        )).scalars().all()
        if not part_colours:
            return

        existing = await self.db.execute(
            select(ProductVariant.style_part_id, ProductVariant.size_id, ProductVariant.colour_id)
            .where(ProductVariant.product_id == style.product_id, ProductVariant.style_part_id.isnot(None))
        )
        existing_triples = {(row.style_part_id, row.size_id, row.colour_id) for row in existing}

        product = (await self.db.execute(select(Product).where(Product.id == style.product_id))).scalar_one()
        for pc in part_colours:
            size_ids = [s.size_id for s in pc.sizes] or [None]
            for size_id in size_ids:
                key = (pc.style_part_id, size_id, pc.colour_id)
                if key in existing_triples:
                    continue
                sku = await build_variant_sku(self.db, product.code, size_id, pc.colour_id, pc.style_part_id)
                self.db.add(ProductVariant(
                    product_id=style.product_id, sku=sku, size_id=size_id,
                    colour_id=pc.colour_id, style_part_id=pc.style_part_id,
                ))
                existing_triples.add(key)
        await self.db.flush()

    async def _fetch_process_masters(self, processes: list, company_id: UUID) -> dict[UUID, "ProcessMaster"]:
        ids = {p.process_master_id for p in processes if p.process_master_id}
        if not ids:
            return {}
        result = await self.db.execute(
            select(ProcessMaster).where(ProcessMaster.id.in_(ids), ProcessMaster.company_id == company_id)
        )
        return {pm.id: pm for pm in result.scalars().all()}

    def _build_style_process(self, style_id: UUID, proc: StyleProcessIn, masters: dict, now: datetime) -> StyleProcess:
        """Builds a StyleProcess row, filling tolerance/unit/rate fields from
        the linked ProcessMaster's defaults only where the style-specific
        value is None — the style-specific value always wins (§26).
        """
        master = masters.get(proc.process_master_id) if proc.process_master_id else None
        return StyleProcess(
            style_id=style_id, seq=proc.seq, process_name=proc.process_name,
            process_master_id=proc.process_master_id, style_part_id=proc.style_part_id,
            is_enabled=proc.is_enabled,
            tolerance_pct=proc.tolerance_pct if proc.tolerance_pct is not None else (master.default_tolerance_pct if master else None),
            input_unit=proc.input_unit if proc.input_unit is not None else (master.default_unit if master else None),
            output_unit=proc.output_unit if proc.output_unit is not None else (master.default_unit if master else None),
            conversion_rule=proc.conversion_rule,
            min_rate=proc.min_rate if proc.min_rate is not None else (master.default_min_rate if master else None),
            max_rate=proc.max_rate if proc.max_rate is not None else (master.default_max_rate if master else None),
            planned_rate=proc.planned_rate if proc.planned_rate is not None else (master.default_planned_rate if master else None),
            notes=proc.notes, created_at=now,
        )

    async def _fetch_size_chart_items(self, sizes: list, company_id: UUID) -> dict[tuple, Decimal | None]:
        """Returns {(size_chart_id, size_id): quantity} for every chart
        referenced by `sizes`, scoped to this company.
        """
        chart_ids = {s.size_chart_id for s in sizes if s.size_chart_id}
        if not chart_ids:
            return {}
        result = await self.db.execute(
            select(SizeChartItem.size_chart_id, SizeChartItem.size_id, SizeChartItem.quantity)
            .join(SizeChart, SizeChart.id == SizeChartItem.size_chart_id)
            .where(SizeChartItem.size_chart_id.in_(chart_ids), SizeChart.company_id == company_id)
        )
        return {(row.size_chart_id, row.size_id): row.quantity for row in result.all()}

    def _build_style_size(self, style_id: UUID, sz: StyleSizeIn, chart_items: dict, now: datetime) -> StyleSize:
        """Builds a StyleSize row, falling back to the linked SizeChartItem's
        quantity only when the incoming style-specific quantity is None —
        the style-specific value always wins (§26, same rule as processes).
        """
        quantity = sz.quantity
        if quantity is None and sz.size_chart_id:
            quantity = chart_items.get((sz.size_chart_id, sz.size_id))
        return StyleSize(
            style_id=style_id, size_id=sz.size_id, sort_order=sz.sort_order,
            quantity=quantity, size_chart_id=sz.size_chart_id, created_at=now,
        )

    # ── Size Chart Master ────────────────────────────────────────────────

    async def list_size_charts(self, company_id: UUID) -> list[SizeChart]:
        result = await self.db.execute(
            select(SizeChart).where(SizeChart.company_id == company_id)
            .options(selectinload(SizeChart.items)).order_by(SizeChart.name)
        )
        return result.scalars().all()

    async def get_size_chart(self, chart_id: UUID, company_id: UUID) -> SizeChart | None:
        result = await self.db.execute(
            select(SizeChart).where(SizeChart.id == chart_id, SizeChart.company_id == company_id)
            .options(selectinload(SizeChart.items))
        )
        return result.scalar_one_or_none()

    async def create_size_chart(self, body: SizeChartCreate, company_id: UUID) -> SizeChart:
        now = datetime.now(timezone.utc)
        chart = SizeChart(company_id=company_id, name=body.name, created_at=now)
        self.db.add(chart)
        await self.db.flush()
        for it in body.items:
            self.db.add(SizeChartItem(size_chart_id=chart.id, size_id=it.size_id, quantity=it.quantity, sort_order=it.sort_order))
        await self.db.flush()
        return await self.get_size_chart(chart.id, company_id)

    async def update_size_chart(self, chart_id: UUID, body: SizeChartCreate, company_id: UUID) -> SizeChart | None:
        chart = await self.get_size_chart(chart_id, company_id)
        if not chart:
            return None
        chart.name = body.name
        await self.db.execute(delete(SizeChartItem).where(SizeChartItem.size_chart_id == chart_id))
        await self.db.flush()
        for it in body.items:
            self.db.add(SizeChartItem(size_chart_id=chart_id, size_id=it.size_id, quantity=it.quantity, sort_order=it.sort_order))
        await self.db.flush()
        # `chart` was loaded above before the delete+reinsert — its `items`
        # collection is stale in the session identity map (the exact bug
        # fixed for update_style in Phase 2). Expire before the re-fetch.
        self.db.expire(chart)
        return await self.get_size_chart(chart_id, company_id)

    async def delete_size_chart(self, chart_id: UUID, company_id: UUID) -> bool:
        chart = await self.get_size_chart(chart_id, company_id)
        if not chart:
            return False
        await self.db.delete(chart)
        await self.db.flush()
        return True

    async def create_style(self, body: StyleCreate, company_id: UUID, user_id: UUID) -> Style:
        """Create a Style Master: the complete production blueprint.

        Every section (sizes, colours, yarn, fabric, process workflow with
        sub-processes/tolerance/units/rates, trims, packing materials) is
        persisted in one transaction — see
        Garments_ERP_Style_Master_Specification.md §21.
        """
        now = datetime.now(timezone.utc)
        product_id = await self._resolve_style_product(body, company_id, user_id)
        s = Style(
            company_id=company_id, created_at=now, created_by=user_id,
            name=body.name, code=body.code, description=body.description,
            garment_type=body.garment_type, gender=body.gender, season=body.season,
            final_output_unit=body.final_output_unit, target_price=body.target_price,
            pieces_per_box=body.pieces_per_box, fabric_source=body.fabric_source,
            product_id=product_id, brand_id=body.brand_id,
        )
        self.db.add(s)
        await self.db.flush()

        size_chart_items = await self._fetch_size_chart_items(body.sizes, company_id)
        for sz in body.sizes:
            self.db.add(self._build_style_size(s.id, sz, size_chart_items, now))

        for cl in body.colours:
            self.db.add(StyleColour(style_id=s.id, colour_id=cl.colour_id, sort_order=cl.sort_order, created_at=now))

        for pc in body.part_colours:
            spc = StylePartColour(
                style_id=s.id, style_part_id=pc.style_part_id, colour_id=pc.colour_id,
                sort_order=pc.sort_order, created_at=now,
            )
            self.db.add(spc)
            await self.db.flush()
            for psz in pc.sizes:
                self.db.add(StylePartSize(style_part_colour_id=spc.id, size_id=psz.size_id, quantity=psz.quantity, sort_order=psz.sort_order))

        fabric_ids: list[UUID] = []
        for fb in body.fabrics:
            sf = StyleFabric(
                style_id=s.id, fabric_name=fb.fabric_name, lot_id=fb.lot_id,
                style_part_id=fb.style_part_id, colour_id=fb.colour_id, source_type=fb.source_type,
                knit_dia=fb.knit_dia, finish_dia=fb.finish_dia,
                consumption=fb.consumption, unit=fb.unit, excess_pct=fb.excess_pct,
                gsm=fb.gsm, dyeing_rate=fb.dyeing_rate, printing_rate=fb.printing_rate,
                notes=fb.notes, created_at=now,
            )
            self.db.add(sf)
            await self.db.flush()
            fabric_ids.append(sf.id)
            for fsz in fb.size_breakdown:
                self.db.add(StyleFabricSize(style_fabric_id=sf.id, size_id=fsz.size_id, quantity=fsz.quantity))

        for yn in body.yarns:
            self.db.add(StyleYarn(
                style_id=s.id, yarn_name=yn.yarn_name, lot_id=yn.lot_id,
                style_fabric_id=fabric_ids[yn.fabric_index] if yn.fabric_index is not None else None,
                colour_id=yn.colour_id, counts=yn.counts, consumption_pct=yn.consumption_pct,
                quantity=yn.quantity, unit=yn.unit, notes=yn.notes, created_at=now,
            ))

        process_masters = await self._fetch_process_masters(body.processes, company_id)
        for proc in body.processes:
            p = self._build_style_process(s.id, proc, process_masters, now)
            self.db.add(p)
            await self.db.flush()
            for sub in proc.sub_processes:
                self.db.add(StyleSubProcess(
                    style_process_id=p.id, seq=sub.seq, name=sub.name,
                    min_rate=sub.min_rate, max_rate=sub.max_rate, planned_rate=sub.planned_rate,
                    notes=sub.notes, created_at=now,
                ))

        for tr in body.trims:
            t = StyleTrim(
                style_id=s.id, trim_name=tr.trim_name, lot_id=tr.lot_id,
                style_part_id=tr.style_part_id, colour_id=tr.colour_id,
                quantity=tr.quantity, unit=tr.unit, category=tr.category,
                process_seq=tr.process_seq,
                excess_pct=tr.excess_pct, notes=tr.notes, created_at=now,
            )
            self.db.add(t)
            await self.db.flush()
            for tsz in tr.size_breakdown:
                self.db.add(StyleTrimSize(style_trim_id=t.id, size_id=tsz.size_id, quantity=tsz.quantity))

        for pm in body.packing_materials:
            self.db.add(StylePackingMaterial(
                style_id=s.id, material_name=pm.material_name, product_id=pm.product_id, quantity=pm.quantity,
                unit=pm.unit, excess_pct=pm.excess_pct,
                consumption_stage=pm.consumption_stage, notes=pm.notes, created_at=now,
            ))

        for ac in body.additional_costs:
            self.db.add(StyleAdditionalCost(
                style_id=s.id, cost_type=ac.cost_type, description=ac.description,
                amount=ac.amount, basis=ac.basis, party_vendor_id=ac.party_vendor_id,
                notes=ac.notes, created_at=now,
            ))

        await self.db.flush()
        style = await self.get_style(s.id, company_id)
        await self._ensure_variants(style)
        await self._ensure_part_variants(style)
        return style

    async def clone_style(self, style_id: UUID, company_id: UUID, user_id: UUID) -> Style | None:
        """Clone an existing Style into a new, independently-editable Style.

        Per Garments_ERP_Style_Master_Specification.md §47.22: fetch the source,
        build a fresh create-payload from it, and reuse create_style() so the
        clone goes through the exact same validated insert path as a normal new
        Style rather than a bespoke deep-copy.
        """
        source = await self.get_style(style_id, company_id)
        if not source:
            return None

        _fabric_index_by_id = {fb.id: i for i, fb in enumerate(source.fabrics)}
        payload = StyleCreate(
            name=f"{source.name} (Copy)", code=None, description=source.description,
            garment_type=source.garment_type, gender=source.gender, season=source.season,
            final_output_unit=source.final_output_unit, target_price=source.target_price,
            pieces_per_box=source.pieces_per_box, fabric_source=source.fabric_source,
            sizes=[{"size_id": x.size_id, "sort_order": x.sort_order, "quantity": x.quantity, "size_chart_id": x.size_chart_id} for x in source.sizes],
            colours=[{"colour_id": x.colour_id, "sort_order": x.sort_order} for x in source.colours],
            part_colours=[{
                "style_part_id": x.style_part_id, "colour_id": x.colour_id, "sort_order": x.sort_order,
                "sizes": [{"size_id": sz.size_id, "quantity": sz.quantity, "sort_order": sz.sort_order} for sz in x.sizes],
            } for x in source.part_colours],
            yarns=[{
                "yarn_name": x.yarn_name, "lot_id": x.lot_id,
                "fabric_index": _fabric_index_by_id.get(x.style_fabric_id),
                "colour_id": x.colour_id, "counts": x.counts, "consumption_pct": x.consumption_pct,
                "quantity": x.quantity, "unit": x.unit, "notes": x.notes,
            } for x in source.yarns],
            fabrics=[{"fabric_name": x.fabric_name, "lot_id": x.lot_id, "consumption": x.consumption,
                       "style_part_id": x.style_part_id, "colour_id": x.colour_id, "source_type": x.source_type,
                       "knit_dia": x.knit_dia, "finish_dia": x.finish_dia,
                       "unit": x.unit, "excess_pct": x.excess_pct, "gsm": x.gsm,
                       "dyeing_rate": x.dyeing_rate, "printing_rate": x.printing_rate, "notes": x.notes,
                       "size_breakdown": [{"size_id": sb.size_id, "quantity": sb.quantity} for sb in x.size_breakdown]}
                      for x in source.fabrics],
            processes=[{
                "seq": p.seq, "process_name": p.process_name, "process_master_id": p.process_master_id,
                "style_part_id": p.style_part_id, "is_enabled": p.is_enabled,
                "tolerance_pct": p.tolerance_pct, "input_unit": p.input_unit, "output_unit": p.output_unit,
                "conversion_rule": p.conversion_rule, "min_rate": p.min_rate, "max_rate": p.max_rate,
                "planned_rate": p.planned_rate, "notes": p.notes,
                "sub_processes": [{"seq": sp.seq, "name": sp.name, "min_rate": sp.min_rate, "max_rate": sp.max_rate, "planned_rate": sp.planned_rate, "notes": sp.notes} for sp in p.sub_processes],
            } for p in source.processes],
            trims=[{"trim_name": x.trim_name, "lot_id": x.lot_id, "style_part_id": x.style_part_id, "colour_id": x.colour_id,
                     "quantity": x.quantity, "unit": x.unit,
                     "category": x.category, "process_seq": x.process_seq, "excess_pct": x.excess_pct, "notes": x.notes,
                     "size_breakdown": [{"size_id": sb.size_id, "quantity": sb.quantity} for sb in x.size_breakdown]}
                    for x in source.trims],
            packing_materials=[{"material_name": x.material_name, "product_id": x.product_id, "quantity": x.quantity, "unit": x.unit,
                                  "excess_pct": x.excess_pct, "consumption_stage": x.consumption_stage,
                                  "notes": x.notes} for x in source.packing_materials],
            additional_costs=[{"cost_type": x.cost_type, "description": x.description, "amount": x.amount,
                                 "basis": x.basis, "party_vendor_id": x.party_vendor_id, "notes": x.notes}
                                for x in source.additional_costs],
        )
        return await self.create_style(payload, company_id, user_id)

    async def update_style(self, style_id: UUID, body: StyleCreate, company_id: UUID, user_id: UUID) -> Style | None:
        """Update a Style Master: full replace of scalar fields and every child section.

        This never touches existing LOTs — a LOT's production_stages were
        snapshotted from the Style at creation time and are independent rows
        from that moment on (see Garments_ERP_Style_Master_Specification.md §2).
        """
        s = await self.get_style(style_id, company_id)
        if not s:
            return None

        now = datetime.now(timezone.utc)
        s.name = body.name
        s.code = body.code
        s.description = body.description
        s.garment_type = body.garment_type
        s.gender = body.gender
        s.season = body.season
        s.final_output_unit = body.final_output_unit
        s.pieces_per_box = body.pieces_per_box
        s.fabric_source = body.fabric_source
        s.target_price = body.target_price
        s.product_id = await self._resolve_style_product(body, company_id, user_id, existing_product_id=s.product_id)
        s.brand_id = body.brand_id
        s.updated_at = now

        await self.db.execute(delete(StyleSize).where(StyleSize.style_id == style_id))
        await self.db.execute(delete(StyleColour).where(StyleColour.style_id == style_id))
        await self.db.execute(delete(StylePartColour).where(StylePartColour.style_id == style_id))
        await self.db.execute(delete(StyleYarn).where(StyleYarn.style_id == style_id))
        await self.db.execute(delete(StyleFabric).where(StyleFabric.style_id == style_id))
        await self.db.execute(delete(StyleProcess).where(StyleProcess.style_id == style_id))
        await self.db.execute(delete(StyleTrim).where(StyleTrim.style_id == style_id))
        await self.db.execute(delete(StylePackingMaterial).where(StylePackingMaterial.style_id == style_id))
        await self.db.execute(delete(StyleAdditionalCost).where(StyleAdditionalCost.style_id == style_id))
        await self.db.flush()

        size_chart_items = await self._fetch_size_chart_items(body.sizes, company_id)
        for sz in body.sizes:
            self.db.add(self._build_style_size(style_id, sz, size_chart_items, now))

        for cl in body.colours:
            self.db.add(StyleColour(style_id=style_id, colour_id=cl.colour_id, sort_order=cl.sort_order, created_at=now))

        for pc in body.part_colours:
            spc = StylePartColour(
                style_id=style_id, style_part_id=pc.style_part_id, colour_id=pc.colour_id,
                sort_order=pc.sort_order, created_at=now,
            )
            self.db.add(spc)
            await self.db.flush()
            for psz in pc.sizes:
                self.db.add(StylePartSize(style_part_colour_id=spc.id, size_id=psz.size_id, quantity=psz.quantity, sort_order=psz.sort_order))

        fabric_ids: list[UUID] = []
        for fb in body.fabrics:
            sf = StyleFabric(
                style_id=style_id, fabric_name=fb.fabric_name, lot_id=fb.lot_id,
                style_part_id=fb.style_part_id, colour_id=fb.colour_id, source_type=fb.source_type,
                knit_dia=fb.knit_dia, finish_dia=fb.finish_dia,
                consumption=fb.consumption, unit=fb.unit, excess_pct=fb.excess_pct,
                gsm=fb.gsm, dyeing_rate=fb.dyeing_rate, printing_rate=fb.printing_rate,
                notes=fb.notes, created_at=now,
            )
            self.db.add(sf)
            await self.db.flush()
            fabric_ids.append(sf.id)
            for fsz in fb.size_breakdown:
                self.db.add(StyleFabricSize(style_fabric_id=sf.id, size_id=fsz.size_id, quantity=fsz.quantity))

        for yn in body.yarns:
            self.db.add(StyleYarn(
                style_id=style_id, yarn_name=yn.yarn_name, lot_id=yn.lot_id,
                style_fabric_id=fabric_ids[yn.fabric_index] if yn.fabric_index is not None else None,
                colour_id=yn.colour_id, counts=yn.counts, consumption_pct=yn.consumption_pct,
                quantity=yn.quantity, unit=yn.unit, notes=yn.notes, created_at=now,
            ))

        process_masters = await self._fetch_process_masters(body.processes, company_id)
        for proc in body.processes:
            p = self._build_style_process(style_id, proc, process_masters, now)
            self.db.add(p)
            await self.db.flush()
            for sub in proc.sub_processes:
                self.db.add(StyleSubProcess(
                    style_process_id=p.id, seq=sub.seq, name=sub.name,
                    min_rate=sub.min_rate, max_rate=sub.max_rate, planned_rate=sub.planned_rate,
                    notes=sub.notes, created_at=now,
                ))

        for tr in body.trims:
            t = StyleTrim(
                style_id=style_id, trim_name=tr.trim_name, lot_id=tr.lot_id,
                style_part_id=tr.style_part_id, colour_id=tr.colour_id,
                quantity=tr.quantity, unit=tr.unit, category=tr.category,
                process_seq=tr.process_seq,
                excess_pct=tr.excess_pct, notes=tr.notes, created_at=now,
            )
            self.db.add(t)
            await self.db.flush()
            for tsz in tr.size_breakdown:
                self.db.add(StyleTrimSize(style_trim_id=t.id, size_id=tsz.size_id, quantity=tsz.quantity))

        for pm in body.packing_materials:
            self.db.add(StylePackingMaterial(
                style_id=style_id, material_name=pm.material_name, product_id=pm.product_id, quantity=pm.quantity,
                unit=pm.unit, excess_pct=pm.excess_pct,
                consumption_stage=pm.consumption_stage, notes=pm.notes, created_at=now,
            ))

        for ac in body.additional_costs:
            self.db.add(StyleAdditionalCost(
                style_id=style_id, cost_type=ac.cost_type, description=ac.description,
                amount=ac.amount, basis=ac.basis, party_vendor_id=ac.party_vendor_id,
                notes=ac.notes, created_at=now,
            ))

        await self.db.flush()
        # `s` (now `style`) was loaded at the top of this method, before the
        # delete+reinsert of every child section above - its relationship
        # collections (sizes, colours, processes, ...) are stale in the
        # session identity map. Expire so the re-fetch below actually reloads
        # them instead of silently returning the pre-update snapshot.
        self.db.expire(s)
        style = await self.get_style(style_id, company_id)
        await self._ensure_variants(style)
        await self._ensure_part_variants(style)
        return style

    # ── Production Lots ────────────────────────────────────────────────────

    async def list_lots(
        self, company_id: UUID, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[ProductionLot], int]:
        q = (
            select(ProductionLot)
            .where(ProductionLot.company_id == company_id)
            .options(*_LOT_FULL_LOADS)
        )
        if status:
            q = q.where(ProductionLot.status == status)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(ProductionLot.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_lot(self, lot_id: UUID, company_id: UUID) -> ProductionLot | None:
        result = await self.db.execute(
            select(ProductionLot)
            .where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
            .options(*_LOT_FULL_LOADS)
        )
        return result.scalar_one_or_none()

    async def build_lot_bom(self, lot: ProductionLot) -> dict:
        """Consolidated BOM (Phase 6) — one view across Yarn/Fabric/Trims/
        Packing Materials, each line showing required vs. available stock.
        "Available" is only computed where a line is linked to a specific
        received batch (lot_id on the originating Style* row); otherwise
        left unknown (None) rather than guessed.

        Reconciliation (spec rule 15 — don't double-count): a fabric
        sourced "from yarn" is marked informational — its yarn components
        are what's actually procured, not the fabric itself — mirroring
        the reference tool's own "produced from yarn, no separate
        planning needed" convention.
        """
        style_fabric_lot_id = {f.id: f.lot_id for f in (lot.style.fabrics if lot.style else [])}
        style_trim_lot_id = {t.id: t.lot_id for t in (lot.style.trims if lot.style else [])}
        style_yarn_lot_id = {y.id: y.lot_id for y in (lot.style.yarns if lot.style else [])}

        async def _line(name, unit, required, lot_ref_id, extra):
            available = None
            if lot_ref_id:
                available = await self.inv.get_lot_balance(lot_ref_id)
            shortage = None
            if available is not None and required is not None:
                shortage = max(required - available, Decimal("0"))
            return {
                "name": name, "unit": unit, "required_qty": required,
                "available_qty": available, "shortage_qty": shortage, **extra,
            }

        effective_source = {}
        for fb in lot.lot_fabrics:
            effective_source[fb.id] = fb.source_type or (lot.style.fabric_source if lot.style else "yarn")

        fabric_lines = []
        for fb in lot.lot_fabrics:
            is_from_yarn = effective_source.get(fb.id) == "yarn"
            fabric_lines.append(await _line(
                fb.fabric_name, fb.unit, fb.planned_qty,
                style_fabric_lot_id.get(fb.style_fabric_id),
                {
                    "id": fb.id, "category": "fabric",
                    "style_part_name": fb.style_part.name if fb.style_part else None,
                    "colour_name": fb.colour.name if fb.colour else None,
                    "is_informational": is_from_yarn,
                    "notes": "Produced from yarn — no separate planning needed" if is_from_yarn else None,
                },
            ))

        yarn_lines = []
        for yn in lot.lot_yarns:
            yarn_lines.append(await _line(
                yn.yarn_name, yn.unit, yn.planned_qty,
                style_yarn_lot_id.get(yn.style_yarn_id),
                {
                    "id": yn.id, "category": "yarn",
                    "colour_name": yn.colour.name if yn.colour else None,
                    "is_informational": False, "notes": None,
                },
            ))

        trim_lines = []
        for tr in lot.trims:
            trim_lines.append(await _line(
                tr.trim_name, tr.unit, tr.planned_qty,
                style_trim_lot_id.get(tr.style_trim_id),
                {"id": tr.id, "category": "trim", "style_part_name": None, "colour_name": None, "is_informational": False, "notes": None},
            ))

        packing_lines = []
        for pm in lot.packing_materials:
            available = None
            if pm.product_id:
                available = await self.inv.get_total_balance(lot.company_id, pm.product_id)
            shortage = max(pm.planned_qty - available, Decimal("0")) if (available is not None and pm.planned_qty is not None) else None
            packing_lines.append({
                "id": pm.id, "category": "packing", "name": pm.material_name, "unit": pm.unit,
                "required_qty": pm.planned_qty, "available_qty": available, "shortage_qty": shortage,
                "style_part_name": None, "colour_name": None, "is_informational": False, "notes": None,
            })

        all_lines = fabric_lines + yarn_lines + trim_lines + packing_lines
        return {
            "production_lot_id": lot.id, "lot_number": lot.lot_number,
            "fabric": fabric_lines, "yarn": yarn_lines, "trims": trim_lines, "packing_materials": packing_lines,
            "total_lines": len(all_lines),
            "shortage_lines": sum(1 for l in all_lines if l["shortage_qty"] not in (None, Decimal("0"))),
        }

    async def update_stage_size(
        self, stage_id: UUID, size_id: UUID, body: StageSizeUpdate, company_id: UUID,
    ) -> ProductionStageSize | None:
        """Record size-wise Accepted/Rejected/Rework for one stage (Phase 9
        — Checking: "receive only quantities released from Cutting", don't
        send rejected items to Packing unless the workflow permits it).
        accepted + rejected + rework can never exceed what came in for that
        size — same validation discipline as the existing aggregate check.
        """
        result = await self.db.execute(
            select(ProductionStageSize)
            .join(ProductionStage, ProductionStage.id == ProductionStageSize.production_stage_id)
            .where(
                ProductionStageSize.production_stage_id == stage_id,
                ProductionStageSize.size_id == size_id,
                ProductionStage.production_lot_id.in_(
                    select(ProductionLot.id).where(ProductionLot.company_id == company_id)
                ),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        accepted = body.accepted_qty if body.accepted_qty is not None else row.accepted_qty
        rejected = body.rejected_qty if body.rejected_qty is not None else row.rejected_qty
        rework = body.rework_qty if body.rework_qty is not None else row.rework_qty
        if accepted + rejected + rework > row.input_qty:
            raise QuantityValidationError(
                f"Accepted + Rejected + Rework ({accepted + rejected + rework}) cannot exceed "
                f"the incoming quantity for this size ({row.input_qty})."
            )
        row.accepted_qty = accepted
        row.rejected_qty = rejected
        row.rework_qty = rework
        if body.defect_reason is not None:
            row.defect_reason = body.defect_reason or None
        row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Mirror _propagate_to_next_stage, but at size granularity: the next
        # stage's per-size input_qty was only ever seeded on the lot's FIRST
        # stage (create_lot, above) — every later stage starts at 0 with no
        # path to fill it in, which silently blocks size-wise tracking past
        # stage 1. Push this size's newly-accepted qty into the next stage's
        # own ProductionStageSize row (creating it if this is its first size
        # update), the same way the aggregate planned_qty already flows.
        stage = (await self.db.execute(select(ProductionStage).where(ProductionStage.id == stage_id))).scalar_one()
        nxt = await self._next_stage(stage)
        if nxt is not None:
            nxt_row = (await self.db.execute(
                select(ProductionStageSize).where(
                    ProductionStageSize.production_stage_id == nxt.id, ProductionStageSize.size_id == size_id,
                )
            )).scalar_one_or_none()
            if nxt_row is None:
                self.db.add(ProductionStageSize(
                    production_stage_id=nxt.id, size_id=size_id, input_qty=accepted, updated_at=datetime.now(timezone.utc),
                ))
            else:
                nxt_row.input_qty = accepted
                nxt_row.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
        return row

    # Stage-type buckets for the "Completed (Consolidated)" view — Cutting
    # covers all pre-QC making/finishing work, Checking is QC, Packing is
    # packing, matching the same vocabulary the lot's own status uses.
    _SUMMARY_BUCKETS: list[tuple[str, str, set[str]]] = [
        ("cutting", "Cutting", {"cutting", "making", "finishing"}),
        ("checking", "Checking", {"qc"}),
        ("packing", "Packing", {"packing", "dispatch"}),
    ]

    def build_lot_production_summary(self, lot: ProductionLot) -> dict:
        """The "Completed (Consolidated)" view (Phase 9) — every figure
        derived from stage transactions (ProductionStageSize rollups
        across all stages in each bucket), never a separately-maintained
        total, per the spec's own rule.
        """
        buckets = []
        cut_qty = checked_qty = accepted_qty = packed_qty = rejected_qty = rework_qty = 0
        for key, label, stage_types in self._SUMMARY_BUCKETS:
            relevant = [s for s in lot.stages if s.stage_type in stage_types]
            b_input = b_accepted = b_rejected = b_rework = 0
            for st in relevant:
                for sz in st.sizes:
                    b_input += sz.input_qty
                    b_accepted += sz.accepted_qty
                    b_rejected += sz.rejected_qty
                    b_rework += sz.rework_qty
            b_pending = max(b_input - b_accepted - b_rejected - b_rework, 0)
            buckets.append({
                "stage_type": key, "label": label, "input_qty": b_input,
                "accepted_qty": b_accepted, "rejected_qty": b_rejected,
                "rework_qty": b_rework, "pending_qty": b_pending,
            })
            rejected_qty += b_rejected
            rework_qty += b_rework
            if key == "cutting":
                cut_qty = b_accepted
            elif key == "checking":
                checked_qty = b_input
                accepted_qty = b_accepted
            elif key == "packing":
                packed_qty = b_accepted

        return {
            "production_lot_id": lot.id, "lot_number": lot.lot_number, "planned_qty": lot.planned_qty,
            "cut_qty": cut_qty, "checked_qty": checked_qty, "accepted_qty": accepted_qty, "packed_qty": packed_qty,
            "rejected_qty": rejected_qty, "rework_qty": rework_qty,
            "remaining_qty": max(lot.planned_qty - packed_qty, 0),
            "buckets": buckets,
        }

    async def _dispatch_reconciliation(self, lot: ProductionLot) -> tuple[Decimal, Decimal]:
        """Dispatch and DC reconciliation (Phase 11) — how much of what this
        lot produced has actually shipped, and how much of that came back.
        The only linkage between a production lot and its deliveries today
        is indirect (lot -> sales order -> delivery items against that
        order's line items); a lot never linked to a sales order has
        nothing to reconcile against, which is reported as 0/0 rather than
        guessed."""
        if not lot.sales_order_id:
            return Decimal("0"), Decimal("0")
        result = await self.db.execute(
            text("""
                SELECT
                    COALESCE((SELECT SUM(di.quantity) FROM delivery_items di
                              JOIN deliveries d ON d.id = di.delivery_id
                              WHERE d.sales_order_id = :so), 0) AS dispatched,
                    COALESCE((SELECT SUM(sri.quantity) FROM sales_return_items sri
                              JOIN delivery_items di2 ON di2.id = sri.delivery_item_id
                              JOIN deliveries d2 ON d2.id = di2.delivery_id
                              WHERE d2.sales_order_id = :so), 0) AS returned
            """),
            {"so": str(lot.sales_order_id)},
        )
        row = result.first()
        return Decimal(row.dispatched), Decimal(row.returned)

    async def build_production_dashboard(self, company_id: UUID) -> dict:
        """Production Progress Dashboard (Phase 11) — consolidates, across
        every non-cancelled lot: size/colour pending quantities (via the
        Phase 9 production summary), material shortages (via the Phase 6
        BOM), process-wise rejection/rework, production cost variance (via
        the existing cost summary), and dispatch/DC reconciliation. Every
        figure is read from the same, already-correct per-lot computations
        used elsewhere (get_lot/build_lot_bom/build_lot_production_summary/
        compute_lot_cost_summary) rather than a second, parallel
        calculation that could disagree with them.
        """
        lot_ids_result = await self.db.execute(
            select(ProductionLot.id)
            .where(ProductionLot.company_id == company_id, ProductionLot.status != "cancelled")
            .order_by(ProductionLot.created_at.desc())
        )
        lot_ids = [r[0] for r in lot_ids_result.fetchall()]

        rows: list[dict] = []
        totals = {
            "lots": 0, "planned_qty": 0, "produced_qty": 0, "pending_qty": 0,
            "rejected_qty": 0, "rework_qty": 0, "material_shortage_lines": 0,
            "cost_planned": Decimal("0"), "cost_actual": Decimal("0"), "cost_variance_amount": Decimal("0"),
            "dispatched_qty": Decimal("0"), "returned_qty": Decimal("0"),
        }
        lots_by_status: dict[str, int] = {}

        for lid in lot_ids:
            lot = await self.get_lot(lid, company_id)
            if not lot:
                continue
            summary = self.build_lot_production_summary(lot)
            bom = await self.build_lot_bom(lot)
            selling_prices = await self.resolve_selling_prices(lot)
            cost = compute_lot_cost_summary(lot, selling_prices)
            dispatched_qty, returned_qty = await self._dispatch_reconciliation(lot)

            cost_planned = cost.total_planned or Decimal("0")
            variance_amount = cost_planned - cost.total_actual

            rows.append({
                "lot_id": lot.id, "lot_number": lot.lot_number,
                "style_name": lot.style.name if lot.style else None,
                "customer_id": lot.customer_id, "status": lot.status,
                "planned_qty": lot.planned_qty, "produced_qty": lot.actual_qty,
                "pending_qty": summary["remaining_qty"], "rejected_qty": summary["rejected_qty"],
                "rework_qty": summary["rework_qty"], "yield_pct": cost.yield_pct,
                "material_shortage_lines": bom["shortage_lines"],
                "cost_planned": cost_planned, "cost_actual": cost.total_actual,
                "cost_variance_amount": variance_amount,
                "dispatched_qty": dispatched_qty, "returned_qty": returned_qty,
                "undispatched_qty": max(Decimal(lot.actual_qty) - dispatched_qty, Decimal("0")),
            })

            totals["lots"] += 1
            totals["planned_qty"] += lot.planned_qty
            totals["produced_qty"] += lot.actual_qty
            totals["pending_qty"] += summary["remaining_qty"]
            totals["rejected_qty"] += summary["rejected_qty"]
            totals["rework_qty"] += summary["rework_qty"]
            totals["material_shortage_lines"] += bom["shortage_lines"]
            totals["cost_planned"] += cost_planned
            totals["cost_actual"] += cost.total_actual
            totals["cost_variance_amount"] += variance_amount
            totals["dispatched_qty"] += dispatched_qty
            totals["returned_qty"] += returned_qty
            lots_by_status[lot.status] = lots_by_status.get(lot.status, 0) + 1

        return {"rows": rows, "totals": totals, "lots_by_status": lots_by_status}

    # Style process names don't carry a stage_type (cutting/making/finishing/qc/
    # packing/dispatch) the way ProductionStage requires; this maps the
    # business-workflow vocabulary from the spec onto that fixed enum so any
    # configured process name still lands in a valid stage_type bucket.
    _STAGE_TYPE_KEYWORDS: list[tuple[str, str]] = [
        ("cut", "cutting"), ("qc", "qc"), ("check", "qc"), ("inspect", "qc"),
        ("pack", "packing"), ("dispatch", "dispatch"), ("iron", "finishing"),
        ("finish", "finishing"), ("trim", "finishing"),
    ]

    def _infer_stage_type(self, process_name: str) -> str:
        lowered = process_name.lower()
        for keyword, stage_type in self._STAGE_TYPE_KEYWORDS:
            if keyword in lowered:
                return stage_type
        return "making"

    async def create_lot(self, body: ProductionLotCreate, company_id: UUID, user_id: UUID) -> ProductionLot:
        """Create a LOT — the actual production instance of a Style.

        Per Garments_ERP_Style_Master_Specification.md §2/§22/§25, the LOT
        snapshots the Style Master's configured process workflow (not a
        hard-coded universal sequence) plus its final output unit and
        version at creation time; later edits to the Style must not
        retroactively change this LOT.
        """
        now = datetime.now(timezone.utc)
        lot_number = (body.lot_number or "").strip() or await self._next_lot_number(company_id)

        style: Style | None = None
        if body.style_id:
            style_result = await self.db.execute(
                select(Style)
                .where(Style.id == body.style_id, Style.company_id == company_id)
                .options(
                    selectinload(Style.processes).selectinload(StyleProcess.sub_processes),
                    selectinload(Style.additional_costs),
                    selectinload(Style.sizes),
                    selectinload(Style.trims).selectinload(StyleTrim.size_breakdown),
                    selectinload(Style.packing_materials),
                    selectinload(Style.fabrics).selectinload(StyleFabric.size_breakdown),
                    selectinload(Style.yarns),
                    selectinload(Style.part_colours).selectinload(StylePartColour.sizes),
                )
            )
            style = style_result.scalar_one_or_none()

        # Target price falls back to the Style's baseline (§47.18) when the
        # caller doesn't explicitly set one on the LOT.
        target_sp = body.target_sp
        if target_sp is None and style is not None:
            target_sp = style.target_price

        lot = ProductionLot(
            company_id=company_id, lot_number=lot_number,
            style_id=body.style_id, customer_id=body.customer_id,
            sales_order_id=body.sales_order_id, order_ref=body.order_ref,
            planned_qty=body.planned_qty, colour_id=body.colour_id,
            planned_weight_kg=body.planned_weight_kg, delivery_date=body.delivery_date,
            season=body.season, target_sp=target_sp, notes=body.notes,
            final_output_unit=style.final_output_unit if style else None,
            pieces_per_box=body.pieces_per_box if body.pieces_per_box is not None else (style.pieces_per_box if style else None),
            style_version=style.version if style else None,
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(lot)
        await self.db.flush()

        # Snapshot Style Additional Costs / Agent Commission (§47.14/§47.28) —
        # planned_amount is frozen here; actual_amount is recorded during execution.
        if style:
            for ac in style.additional_costs:
                self.db.add(LotAdditionalCost(
                    production_lot_id=lot.id, style_additional_cost_id=ac.id,
                    cost_type=ac.cost_type, description=ac.description,
                    planned_amount=ac.amount, basis=ac.basis,
                    party_vendor_id=ac.party_vendor_id, notes=ac.notes,
                    created_at=now,
                ))

        for ac in body.additional_costs:
            self.db.add(LotAdditionalCost(
                production_lot_id=lot.id, cost_type=ac.cost_type, description=ac.description,
                planned_amount=ac.planned_amount, actual_amount=ac.actual_amount, basis=ac.basis,
                party_vendor_id=ac.party_vendor_id, notes=ac.notes, created_at=now,
            ))

        resolved_size_qty: dict[UUID, int] = {}
        if body.sizes:
            for sz in body.sizes:
                self.db.add(ProductionLotSize(
                    production_lot_id=lot.id, size_id=sz.size_id, planned_qty=sz.planned_qty,
                ))
                resolved_size_qty[sz.size_id] = sz.planned_qty
        elif style:
            # §1.1: "quantity for each size must be configurable and
            # reusable from Style Creation" - default the LOT's per-size
            # plan from the Style's own quantities when the caller didn't
            # explicitly provide sizes.
            for ssz in style.sizes:
                if ssz.quantity is not None:
                    self.db.add(ProductionLotSize(
                        production_lot_id=lot.id, size_id=ssz.size_id, planned_qty=int(ssz.quantity),
                    ))
                    resolved_size_qty[ssz.size_id] = int(ssz.quantity)

        # Part/Colour/Size planned quantities (Phase 8 — the Order->Style->
        # Part->Colour->Size->Planned Quantity hierarchy at the actual lot
        # level): explicit override wins, else pre-filled from the Style's
        # own part_colours/sizes template, same convention as plain sizes.
        if body.part_colours:
            for pc in body.part_colours:
                lpc = LotPartColour(
                    production_lot_id=lot.id, style_part_id=pc.style_part_id, colour_id=pc.colour_id,
                    sort_order=pc.sort_order, created_at=now,
                )
                self.db.add(lpc)
                await self.db.flush()
                for psz in pc.sizes:
                    self.db.add(LotPartSize(lot_part_colour_id=lpc.id, size_id=psz.size_id, planned_qty=psz.planned_qty, sort_order=0))
        elif style:
            for spc in style.part_colours:
                lpc = LotPartColour(
                    production_lot_id=lot.id, style_part_colour_id=spc.id, style_part_id=spc.style_part_id,
                    colour_id=spc.colour_id, sort_order=spc.sort_order, created_at=now,
                )
                self.db.add(lpc)
                await self.db.flush()
                for ssz in spc.sizes:
                    if ssz.quantity is not None:
                        self.db.add(LotPartSize(lot_part_colour_id=lpc.id, size_id=ssz.size_id, planned_qty=int(ssz.quantity), sort_order=ssz.sort_order))

        # Snapshot Style Trims / Packing Materials (§21: "fetched automatically
        # when the Production Lot is created"). Trims with a size-wise
        # breakdown are summed against this LOT's resolved per-size plan;
        # flat trims and packing materials scale off the LOT's total
        # planned_qty. Either way scaled by excess_pct when set.
        if style:
            for tr in style.trims:
                if tr.size_breakdown:
                    base_qty = sum(
                        float(sb.quantity) * resolved_size_qty.get(sb.size_id, 0)
                        for sb in tr.size_breakdown
                    )
                else:
                    base_qty = float(tr.quantity) * body.planned_qty if tr.quantity is not None else None
                planned_qty = None
                if base_qty is not None:
                    excess_mult = 1 + float(tr.excess_pct) / 100 if tr.excess_pct is not None else 1
                    planned_qty = Decimal(str(base_qty * excess_mult))
                self.db.add(LotTrim(
                    production_lot_id=lot.id, style_trim_id=tr.id, trim_name=tr.trim_name,
                    unit=tr.unit, category=tr.category, planned_qty=planned_qty, created_at=now,
                ))

            for pm in style.packing_materials:
                planned_qty = None
                if pm.quantity is not None:
                    base_qty = float(pm.quantity) * body.planned_qty
                    excess_mult = 1 + float(pm.excess_pct) / 100 if pm.excess_pct is not None else 1
                    planned_qty = Decimal(str(base_qty * excess_mult))
                self.db.add(LotPackingMaterial(
                    production_lot_id=lot.id, style_packing_material_id=pm.id, material_name=pm.material_name,
                    product_id=pm.product_id, unit=pm.unit, consumption_stage=pm.consumption_stage,
                    planned_qty=planned_qty, created_at=now,
                ))

            # Fabric / Yarn requirement snapshot (Phase 6 — BOM Consolidation):
            # same size-breakdown-aware scaling as trims above. A yarn's
            # planned_qty is its consumption_pct share of its parent fabric's
            # own planned_qty (see LotYarn docstring) — computed after the
            # fabric loop so the parent's quantity already exists.
            lot_fabric_by_style_fabric: dict[UUID, LotFabric] = {}
            for fb in style.fabrics:
                if fb.size_breakdown:
                    base_qty = sum(
                        float(sb.quantity) * resolved_size_qty.get(sb.size_id, 0)
                        for sb in fb.size_breakdown
                    )
                else:
                    base_qty = float(fb.consumption) * body.planned_qty if fb.consumption is not None else None
                planned_qty = None
                if base_qty is not None:
                    excess_mult = 1 + float(fb.excess_pct) / 100 if fb.excess_pct is not None else 1
                    planned_qty = Decimal(str(base_qty * excess_mult))
                lf = LotFabric(
                    production_lot_id=lot.id, style_fabric_id=fb.id, fabric_name=fb.fabric_name,
                    style_part_id=fb.style_part_id, colour_id=fb.colour_id, source_type=fb.source_type,
                    unit=fb.unit, planned_qty=planned_qty, created_at=now,
                )
                self.db.add(lf)
                await self.db.flush()
                lot_fabric_by_style_fabric[fb.id] = lf

            for yn in style.yarns:
                lot_fabric = lot_fabric_by_style_fabric.get(yn.style_fabric_id) if yn.style_fabric_id else None
                planned_qty = None
                if lot_fabric is not None and lot_fabric.planned_qty is not None and yn.consumption_pct is not None:
                    planned_qty = (lot_fabric.planned_qty * yn.consumption_pct / 100).quantize(Decimal("0.0001"))
                self.db.add(LotYarn(
                    production_lot_id=lot.id, lot_fabric_id=lot_fabric.id if lot_fabric else None,
                    style_yarn_id=yn.id, yarn_name=yn.yarn_name, colour_id=yn.colour_id,
                    counts=yn.counts, consumption_pct=yn.consumption_pct, unit=yn.unit,
                    planned_qty=planned_qty, created_at=now,
                ))

        # Stages are sorted by created_at for display (ProductionStage has no
        # explicit seq column); stagger by a millisecond per row so creation
        # order — which is the intended process order — sorts deterministically
        # instead of tying on an identical `now` timestamp.
        #
        # Only the FIRST stage is stamped with the LOT's planned_qty — nothing
        # has flowed through the later stages yet, so their planned_qty stays
        # None until the preceding stage's actual accepted output propagates
        # into it (see _propagate_to_next_stage). Previously every stage got
        # the LOT's original planned_qty unconditionally, which is the root
        # cause of a downstream stage showing the LOT quantity instead of the
        # previous stage's actual accepted quantity.
        created_stages: list[ProductionStage] = []
        if style and style.processes:
            for i, proc in enumerate(sorted((p for p in style.processes if p.is_enabled), key=lambda p: p.seq)):
                stage_time = now + timedelta(milliseconds=i)
                st = ProductionStage(
                    production_lot_id=lot.id, style_process_id=proc.id,
                    stage_type=self._infer_stage_type(proc.process_name),
                    stage_name=proc.process_name, planned_qty=body.planned_qty if i == 0 else None,
                    tolerance_pct=proc.tolerance_pct, input_unit=proc.input_unit,
                    output_unit=proc.output_unit, conversion_rule=proc.conversion_rule,
                    min_rate=proc.min_rate, max_rate=proc.max_rate, planned_rate=proc.planned_rate,
                    created_at=stage_time, updated_at=stage_time,
                )
                self.db.add(st)
                created_stages.append(st)
        else:
            # No Style (or Style has no configured workflow) — fall back to
            # the generic garment-production stages so the LOT is still usable.
            default_stages = [
                ("cutting", "Cutting"), ("making", "Making"),
                ("finishing", "Finishing"), ("qc", "QC / Checking"),
                ("packing", "Packing"),
            ]
            for i, (stype, sname) in enumerate(default_stages):
                stage_time = now + timedelta(milliseconds=i)
                st = ProductionStage(
                    production_lot_id=lot.id, stage_type=stype, stage_name=sname,
                    planned_qty=body.planned_qty if i == 0 else None,
                    created_at=stage_time, updated_at=stage_time,
                )
                self.db.add(st)
                created_stages.append(st)

        await self.db.flush()

        # Size-wise detail (Phase 9): one ProductionStageSize row per
        # (stage, size) — only the first stage starts with a real input_qty
        # (mirroring the aggregate planned_qty rule above); later stages
        # start at 0 and are filled in as work actually reaches them.
        if resolved_size_qty:
            for i, st in enumerate(created_stages):
                for size_id, qty in resolved_size_qty.items():
                    self.db.add(ProductionStageSize(
                        production_stage_id=st.id, size_id=size_id,
                        input_qty=qty if i == 0 else 0, updated_at=now,
                    ))
            # This session has autoflush disabled (app/db/session.py) — without
            # an explicit flush here, the rows just added above are invisible
            # to the selectinload below (and to any other query), not just
            # stale-cached.
            await self.db.flush()
        result = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == lot.id).options(*_LOT_FULL_LOADS)
        )
        return result.scalar_one()

    async def _sync_product_pricing(
        self, lot: ProductionLot, *, mrp: Decimal | None = None, cost_price: Decimal | None = None,
    ) -> None:
        """Push a value onto Product.mrp and/or Product.cost_price for every
        distinct product this lot actually produced, so Inventory > Products
        reflects real production economics without a separate manual step.
        """
        product_ids = {o.product_id for o in lot.outputs}
        if not product_ids or (mrp is None and cost_price is None):
            return
        result = await self.db.execute(select(Product).where(Product.id.in_(product_ids)))
        for product in result.scalars().all():
            if mrp is not None:
                product.mrp = mrp
            if cost_price is not None:
                product.cost_price = cost_price

    async def update_lot(self, lot_id: UUID, body: ProductionLotUpdate, company_id: UUID) -> ProductionLot | None:
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        updates = body.model_dump(exclude_unset=True)
        for f, v in updates.items():
            setattr(lot, f, v)
        lot.updated_at = datetime.now(timezone.utc)
        if "actual_selling_price" in updates and lot.actual_selling_price is not None:
            await self._sync_product_pricing(lot, mrp=lot.actual_selling_price)
        await self.db.flush()
        return lot

    # The LOT's own coarse status (item #8 of the 16-item request): Cutting
    # covers all making/finishing work before QC, Checking is QC, Packing is
    # packing — each bucket maps to the ProductionStage.stage_type values
    # already used for floor-level stage logging, so "is this phase done" is
    # read from stages the floor already records rather than a separate flag.
    _LOT_STATUS_FLOW: dict[str, str] = {"cutting": "checking", "checking": "packing", "packing": "completed"}
    _LOT_STAGE_BUCKETS: dict[str, set[str]] = {
        "cutting": {"cutting", "making", "finishing"},
        "checking": {"qc"},
        "packing": {"packing"},
    }

    def _lot_stage_gate(self, lot: ProductionLot) -> list[str]:
        """What's missing before `lot` can leave its current status — empty
        means clear to advance. Spec: "move to next stage only if every
        relevant area filled, otherwise popup should remind them."
        """
        bucket = self._LOT_STAGE_BUCKETS.get(lot.status)
        if bucket is None:
            return []
        relevant = [s for s in lot.stages if s.stage_type in bucket]
        if not relevant:
            return [f"No {lot.status} stage has been logged for this lot yet."]
        incomplete = [s for s in relevant if s.status != "completed"]
        if incomplete:
            names = ", ".join(s.stage_name for s in incomplete)
            return [f"{len(incomplete)} {lot.status} stage(s) still in progress: {names}"]
        return []

    def _audit(
        self, *, company_id: UUID, production_lot_id: UUID, entity_type: str, entity_id: UUID,
        action: str, field_name: str | None, old_value, new_value, user_id: UUID | None,
    ) -> None:
        self.db.add(ProductionAuditLog(
            company_id=company_id, production_lot_id=production_lot_id,
            entity_type=entity_type, entity_id=entity_id, action=action, field_name=field_name,
            old_value=None if old_value is None else str(old_value)[:200],
            new_value=None if new_value is None else str(new_value)[:200],
            changed_by=user_id, changed_at=datetime.now(timezone.utc),
        ))

    async def list_audit_log(self, lot_id: UUID, company_id: UUID) -> list[ProductionAuditLog]:
        result = await self.db.execute(
            select(ProductionAuditLog)
            .where(ProductionAuditLog.production_lot_id == lot_id, ProductionAuditLog.company_id == company_id)
            .order_by(ProductionAuditLog.changed_at.desc())
        )
        return result.scalars().all()

    async def advance_lot_status(
        self, lot_id: UUID, company_id: UUID, new_status: str, user_id: UUID | None = None,
    ) -> ProductionLot | None:
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        if new_status not in self._LOT_STATUS_FLOW.values() and new_status not in ("cancelled", "completed"):
            return None
        if new_status != "cancelled" and self._LOT_STATUS_FLOW.get(lot.status) == new_status:
            missing = self._lot_stage_gate(lot)
            if missing:
                raise BusinessRulesError("STAGE_INCOMPLETE", missing[0])
        old_status = lot.status
        lot.status = new_status
        lot.updated_at = datetime.now(timezone.utc)
        if new_status == "completed":
            lot.closed_at = datetime.now(timezone.utc)
        if old_status != new_status:
            self._audit(company_id=company_id, production_lot_id=lot.id, entity_type="production_lot",
                        entity_id=lot.id, action="status_changed", field_name="status",
                        old_value=old_status, new_value=new_status, user_id=user_id)
        await self.db.flush()
        return lot

    async def reopen_lot(self, lot_id: UUID, company_id: UUID, user_id: UUID | None = None) -> ProductionLot | None:
        """Reopen a cancelled/completed lot back to Cutting."""
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        if lot.status not in ("cancelled", "completed"):
            raise ValueError(f"Only a cancelled or completed lot can be reopened (this one is {lot.status}).")
        old_status = lot.status
        lot.status = "cutting"
        lot.closed_at = None
        lot.updated_at = datetime.now(timezone.utc)
        self._audit(company_id=company_id, production_lot_id=lot.id, entity_type="production_lot",
                    entity_id=lot.id, action="reopened", field_name="status",
                    old_value=old_status, new_value="cutting", user_id=user_id)
        await self.db.flush()
        return lot

    async def delete_lot(self, lot_id: UUID, company_id: UUID) -> bool:
        """Delete a lot. Refused when real inventory movement has already been
        recorded against it (Material Issues consume raw material, Outputs
        receive finished goods) — that accounting trail must not be erased;
        cancel the lot instead. Stages/challans/entries/additional costs/fabric
        processing never touch inventory, so they cascade-delete safely.
        """
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return False
        if lot.material_issues or lot.outputs:
            raise ValueError(
                "Cannot delete a lot with recorded Material Issues or Production Output — "
                "cancel it instead to preserve the inventory trail."
            )
        await self.db.delete(lot)
        await self.db.flush()
        return True

    # ── Stages ─────────────────────────────────────────────────────────────

    async def _next_stage(self, stage: ProductionStage) -> ProductionStage | None:
        """The stage immediately after `stage` in its lot, ordered by
        created_at — the same ordering used everywhere else for display.
        """
        result = await self.db.execute(
            select(ProductionStage)
            .where(
                ProductionStage.production_lot_id == stage.production_lot_id,
                ProductionStage.created_at > stage.created_at,
            )
            .order_by(ProductionStage.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _propagate_to_next_stage(self, stage: ProductionStage) -> None:
        """Push `stage`'s actual accepted output into the immediately-following
        stage's planned_qty — the core stage-to-stage quantity flow rule: the
        next stage plans against what was actually accepted from the previous
        one, never the LOT's original planned quantity.
        """
        nxt = await self._next_stage(stage)
        if nxt is not None:
            nxt.planned_qty = _stage_accepted_qty(stage)
            nxt.updated_at = datetime.now(timezone.utc)

    async def add_stage(self, lot_id: UUID, body: StageCreate, company_id: UUID) -> ProductionStage | None:
        lot_result = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
        )
        lot = lot_result.scalar_one_or_none()
        if not lot:
            return None
        if lot.status in ("completed", "cancelled"):
            raise ValueError(f"Cannot add a stage to a {lot.status} lot")
        now = datetime.now(timezone.utc)

        planned_qty = body.planned_qty
        if planned_qty is None:
            # A stage added after the lot already has stages joins the chain
            # at the end (stages are ordered by created_at) — inherit the
            # current last stage's actual accepted output, same rule as any
            # other stage-to-stage handoff.
            last_result = await self.db.execute(
                select(ProductionStage)
                .where(ProductionStage.production_lot_id == lot_id)
                .order_by(ProductionStage.created_at.desc())
                .limit(1)
            )
            last_stage = last_result.scalar_one_or_none()
            if last_stage is not None:
                accepted = _stage_accepted_qty(last_stage)
                planned_qty = accepted if accepted > 0 else None
            else:
                planned_qty = lot.planned_qty

        stage = ProductionStage(
            production_lot_id=lot_id, stage_type=body.stage_type, stage_name=body.stage_name,
            planned_qty=planned_qty, assignment_type=body.assignment_type,
            vendor_id=body.vendor_id, worker_id=body.worker_id,
            rate_per_pc=body.rate_per_pc, notes=body.notes,
            created_at=now, updated_at=now,
        )
        self.db.add(stage)
        await self.db.flush()
        result = await self.db.execute(
            select(ProductionStage)
            .where(ProductionStage.id == stage.id)
            .options(*_STAGE_OUT_LOADS)
        )
        return result.scalar_one()

    async def fabric_blockers(self, lot: ProductionLot) -> list[str]:
        """Why garment work can't start on this lot yet (spec §33). Empty
        list = fabric-ready, or the lot has no style and so nothing to gate.
        """
        if not lot.style_id:
            return []
        style = (await self.db.execute(select(Style).where(Style.id == lot.style_id))).scalar_one_or_none()
        if not style:
            return []
        has_config = (await self.db.execute(
            select(func.count(StyleFabric.id)).where(StyleFabric.style_id == style.id)
        )).scalar_one() > 0
        issued = (await self.db.execute(
            select(func.coalesce(func.sum(MaterialIssueItem.issued_qty), 0))
            .join(MaterialIssue, MaterialIssue.id == MaterialIssueItem.material_issue_id)
            .join(Product, Product.id == MaterialIssueItem.product_id)
            .where(MaterialIssue.production_lot_id == lot.id, Product.product_type == "fabric")
        )).scalar_one()
        processed = (await self.db.execute(
            select(func.count(FabricProcessingEntry.id)).where(
                FabricProcessingEntry.production_lot_id == lot.id,
                FabricProcessingEntry.status == "completed",
            )
        )).scalar_one()
        result = business_rules.validate_fabric_ready(
            has_fabric_config=has_config, fabric_source=style.fabric_source,
            fabric_issued_qty=Decimal(issued), completed_fabric_processing=processed,
        )
        return [] if result.valid else [result.reason]

    async def _require_fabric_ready(self, lot_id: UUID) -> None:
        lot = (await self.db.execute(select(ProductionLot).where(ProductionLot.id == lot_id))).scalar_one()
        blockers = await self.fabric_blockers(lot)
        if blockers:
            raise BusinessRulesError("fabric_not_ready", blockers[0])

    async def add_stage_entry(
        self, stage_id: UUID, body: StageEntryCreate, user_id: UUID,
    ) -> ProductionStageEntry:
        if body.pieces_in > 0:
            stage_lot_id = (await self.db.execute(
                select(ProductionStage.production_lot_id).where(ProductionStage.id == stage_id)
            )).scalar_one_or_none()
            if stage_lot_id:
                await self._require_fabric_ready(stage_lot_id)
        now = datetime.now(timezone.utc)
        if body.input_weight_kg is not None and body.output_weight_kg is not None:
            remainder = body.input_weight_kg - body.output_weight_kg
            classified = (body.wastage_kg or Decimal("0")) + (body.recoverable_kg or Decimal("0"))
            if classified > remainder:
                raise QuantityValidationError(
                    f"Wastage + Recoverable ({classified} kg) cannot exceed the unaccounted "
                    f"remainder (input - output = {remainder} kg) for this entry."
                )
        entry = ProductionStageEntry(
            stage_id=stage_id, entry_date=body.entry_date,
            pieces_in=body.pieces_in, pieces_out=body.pieces_out, rejected=body.rejected,
            input_weight_kg=body.input_weight_kg, output_weight_kg=body.output_weight_kg,
            wastage_kg=body.wastage_kg, recoverable_kg=body.recoverable_kg,
            operator=body.operator, machine=body.machine, notes=body.notes,
            created_at=now, created_by=user_id,
        )
        self.db.add(entry)
        await self.db.flush()

        # Roll up to stage totals
        stage_res = await self.db.execute(
            select(ProductionStage).where(ProductionStage.id == stage_id)
            .options(selectinload(ProductionStage.challans))
        )
        stage = stage_res.scalar_one_or_none()
        if stage:
            new_input = stage.input_qty + body.pieces_in
            new_output = stage.output_qty + body.pieces_out
            if new_output > new_input:
                raise QuantityValidationError(
                    "Output quantity cannot exceed input quantity for this stage "
                    f"(would be {new_output} out of {new_input} in)."
                )
            stage.input_qty = new_input
            stage.output_qty = new_output
            stage.rejected_qty += body.rejected
            if body.input_weight_kg is not None:
                stage.input_weight_kg = (stage.input_weight_kg or Decimal("0")) + body.input_weight_kg
            if body.output_weight_kg is not None:
                stage.output_weight_kg = (stage.output_weight_kg or Decimal("0")) + body.output_weight_kg
            if body.wastage_kg is not None:
                stage.wastage_kg = (stage.wastage_kg or Decimal("0")) + body.wastage_kg
            if body.recoverable_kg is not None:
                stage.recoverable_kg = (stage.recoverable_kg or Decimal("0")) + body.recoverable_kg
            stage.updated_at = now
            if stage.status == "pending" and body.pieces_in > 0:
                stage.status = "in_progress"
                stage.started_at = now
            if stage.rate_per_pc is not None or any(c.bill_amount for c in stage.challans):
                stage.bill_amount = _stage_actual_cost(stage)
            await self._propagate_to_next_stage(stage)

        await self.db.flush()
        return entry

    # Stage fields worth an audit row when they change — status and the
    # assignment/quantity corrections; stage_name/notes edits are cosmetic.
    _AUDITED_STAGE_FIELDS = ("status", "assignment_type", "vendor_id", "worker_id", "rate_per_pc",
                             "planned_qty", "sent_qty", "received_qty", "rejected_qty")

    async def update_stage(
        self, stage_id: UUID, body: StageUpdate, company_id: UUID, user_id: UUID | None = None,
    ) -> ProductionStage | None:
        result = await self.db.execute(
            select(ProductionStage)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStage.id == stage_id, ProductionLot.company_id == company_id)
            .options(*_STAGE_OUT_LOADS)
        )
        stage = result.scalar_one_or_none()
        if not stage:
            return None

        updates = body.model_dump(exclude_unset=True)

        # Stages are completed in order: a stage can't be completed while an
        # earlier one is still open, and a completed stage can't be reopened
        # once a later one has been completed on top of it.
        new_status = updates.get("status")
        if new_status and new_status != stage.status:
            siblings = (await self.db.execute(
                select(ProductionStage.stage_name, ProductionStage.status, ProductionStage.created_at)
                .where(ProductionStage.production_lot_id == stage.production_lot_id, ProductionStage.id != stage.id)
            )).all()
            if new_status == "completed":
                open_before = [n for n, st, c in siblings if c < stage.created_at and st != "completed"]
                if open_before:
                    raise QuantityValidationError(f"Complete the earlier stage(s) first: {', '.join(open_before)}.")
            elif stage.status == "completed":
                done_after = [n for n, st, c in siblings if c > stage.created_at and st == "completed"]
                if done_after:
                    raise QuantityValidationError(f"Can't reopen — later stage(s) already completed: {', '.join(done_after)}.")

        # Validate any correction to sent/received/rejected as one consistent
        # set (§7 — editing a stage must not create impossible quantities):
        # received + rejected must never exceed sent.
        quantity_touched = any(k in updates for k in ("sent_qty", "received_qty", "rejected_qty"))
        new_sent = updates.get("sent_qty", stage.sent_qty)
        new_received = updates.get("received_qty", stage.received_qty)
        new_rejected = updates.get("rejected_qty", stage.rejected_qty)
        if stage.assignment_type and quantity_touched and new_received + new_rejected > new_sent:
            raise QuantityValidationError(
                f"Received ({new_received}) + Rejected ({new_rejected}) cannot exceed Sent OUT ({new_sent})."
            )

        for field, val in updates.items():
            old = getattr(stage, field)
            if field in self._AUDITED_STAGE_FIELDS and old != val:
                self._audit(company_id=company_id, production_lot_id=stage.production_lot_id,
                            entity_type="production_stage", entity_id=stage.id,
                            action="status_changed" if field == "status" else "corrected",
                            field_name=f"{stage.stage_name}.{field}", old_value=old, new_value=val, user_id=user_id)
            setattr(stage, field, val)
        stage.updated_at = datetime.now(timezone.utc)
        if stage.rate_per_pc is not None or any(c.bill_amount for c in stage.challans):
            stage.bill_amount = _stage_actual_cost(stage)
        if {"sent_qty", "received_qty", "rejected_qty", "assignment_type"} & updates.keys():
            await self._propagate_to_next_stage(stage)
        await self.db.flush()
        return stage

    # ── Stage Challans (Job Work OUT/IN) ────────────────────────────────────

    async def create_challan(
        self, stage_id: UUID, body: StageChallanCreate, company_id: UUID, user_id: UUID,
    ) -> ProductionStageChallan | None:
        result = await self.db.execute(
            select(ProductionStage)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStage.id == stage_id, ProductionLot.company_id == company_id)
        )
        stage = result.scalar_one_or_none()
        if not stage:
            return None
        if body.out_qty > 0:
            await self._require_fabric_ready(stage.production_lot_id)

        # Sent OUT cannot exceed what's actually available from the previous
        # stage (§3) — the stage's own planned_qty, kept in sync by
        # _propagate_to_next_stage.
        available = stage.planned_qty
        if available is None:
            raise QuantityValidationError(
                "Nothing available from the previous stage yet — its output hasn't been recorded."
            )
        if stage.sent_qty + body.out_qty > available:
            raise QuantityValidationError(
                f"Sending {body.out_qty} would total {stage.sent_qty + body.out_qty} sent, "
                f"exceeding the {available} available from the previous stage."
            )

        now = datetime.now(timezone.utc)
        challan_number = await self._next_challan_number(company_id)
        challan = ProductionStageChallan(
            production_stage_id=stage_id, challan_number=challan_number,
            vendor_id=body.vendor_id, worker_id=body.worker_id,
            out_date=body.out_date, out_qty=body.out_qty,
            expected_return_days=body.expected_return_days, notes=body.notes,
            created_at=now, created_by=user_id,
        )
        self.db.add(challan)

        if stage.assignment_type is None:
            stage.assignment_type = "internal_worker" if body.worker_id else "vendor"
        if stage.vendor_id is None and body.vendor_id:
            stage.vendor_id = body.vendor_id
        if stage.worker_id is None and body.worker_id:
            stage.worker_id = body.worker_id
        stage.sent_qty += body.out_qty
        if stage.status == "pending":
            stage.status = "in_progress"
            stage.started_at = now
        stage.updated_at = now

        await self.db.flush()
        return challan

    async def receive_challan(
        self, challan_id: UUID, body: StageChallanReceive, company_id: UUID,
    ) -> ProductionStageChallan | None:
        result = await self.db.execute(
            select(ProductionStageChallan)
            .join(ProductionStage, ProductionStage.id == ProductionStageChallan.production_stage_id)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStageChallan.id == challan_id, ProductionLot.company_id == company_id)
            .options(selectinload(ProductionStageChallan.stage).selectinload(ProductionStage.challans))
        )
        challan = result.scalar_one_or_none()
        if not challan:
            return None
        if body.in_qty > challan.out_qty:
            raise QuantityValidationError(
                f"Received quantity ({body.in_qty}) cannot exceed the quantity sent out ({challan.out_qty})."
            )
        # Explicit rejected_qty distinguishes "rejected" from "still pending
        # with the vendor/worker" (§3) — default to the old fully-reconciled
        # behavior (out - in) when the caller omits it.
        rejected_qty = body.rejected_qty if body.rejected_qty is not None else (challan.out_qty - body.in_qty)
        pending_qty = challan.out_qty - body.in_qty - rejected_qty
        if pending_qty < 0:
            raise QuantityValidationError(
                f"Received ({body.in_qty}) + Rejected ({rejected_qty}) cannot exceed Sent OUT ({challan.out_qty})."
            )

        now = datetime.now(timezone.utc)
        challan.in_date = body.in_date
        challan.in_qty = body.in_qty
        challan.rejected_qty = rejected_qty
        challan.bill_amount = body.bill_amount
        if body.notes is not None:
            challan.notes = body.notes
        challan.status = "received" if pending_qty == 0 else "partial"
        challan.updated_at = now

        stage = challan.stage
        stage.received_qty += body.in_qty
        stage.rejected_qty += rejected_qty
        if stage.status == "pending":
            stage.status = "in_progress"
            stage.started_at = now
        stage.updated_at = now
        if stage.rate_per_pc is not None or any(c.bill_amount for c in stage.challans):
            stage.bill_amount = _stage_actual_cost(stage)
        await self._propagate_to_next_stage(stage)

        await self.db.flush()
        return challan

    # ── Internal Workers ──────────────────────────────────────────────────

    async def list_workers(self, company_id: UUID) -> list[InternalWorker]:
        result = await self.db.execute(
            select(InternalWorker)
            .where(InternalWorker.company_id == company_id, InternalWorker.is_active.is_(True))
            .order_by(InternalWorker.name)
        )
        return result.scalars().all()

    async def create_worker(self, body: InternalWorkerCreate, company_id: UUID, user_id: UUID) -> InternalWorker:
        worker = InternalWorker(
            company_id=company_id, name=body.name, phone=body.phone,
            role_title=body.role_title, daily_rate=body.daily_rate,
            created_at=datetime.now(timezone.utc), created_by=user_id,
        )
        self.db.add(worker)
        await self.db.flush()
        return worker

    async def update_challan_bill(
        self, challan_id: UUID, body: StageChallanBillUpdate, company_id: UUID,
    ) -> ProductionStageChallan | None:
        result = await self.db.execute(
            select(ProductionStageChallan)
            .join(ProductionStage, ProductionStage.id == ProductionStageChallan.production_stage_id)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStageChallan.id == challan_id, ProductionLot.company_id == company_id)
        )
        challan = result.scalar_one_or_none()
        if not challan:
            return None
        challan.bill_received = body.bill_received
        challan.bill_received_date = body.bill_received_date
        if body.notes is not None:
            challan.notes = body.notes
        challan.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return challan

    async def get_challan_for_document(self, challan_id: UUID, company_id: UUID) -> ProductionStageChallan | None:
        """Loads a job-work challan with the full stage -> lot -> style ->
        product -> hsn chain needed to render its Delivery Challan PDF
        (spec §17) - reuses the Style<->Product link from Phase 1 rather
        than duplicating HSN/GST onto the challan itself.
        """
        result = await self.db.execute(
            select(ProductionStageChallan)
            .join(ProductionStage, ProductionStage.id == ProductionStageChallan.production_stage_id)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStageChallan.id == challan_id, ProductionLot.company_id == company_id)
            .options(
                selectinload(ProductionStageChallan.stage)
                .selectinload(ProductionStage.production_lot)
                .selectinload(ProductionLot.style)
                .selectinload(Style.product)
                .selectinload(Product.hsn),
            )
        )
        return result.scalar_one_or_none()

    # ── Fabric Processing (dyeing/printing) ─────────────────────────────────

    async def create_fabric_processing(
        self, lot_id: UUID, body: FabricProcessingCreate, company_id: UUID, user_id: UUID,
    ) -> FabricProcessingEntry | None:
        result = await self.db.execute(
            select(ProductionLot)
            .where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
            .options(selectinload(ProductionLot.style).selectinload(Style.fabrics))
        )
        lot = result.scalar_one_or_none()
        if not lot:
            return None

        rate_per_kg = body.rate_per_kg
        if rate_per_kg is None and lot.style and len(lot.style.fabrics) == 1:
            fabric = lot.style.fabrics[0]
            rate_per_kg = fabric.dyeing_rate if body.process_type == "dyeing" else (
                fabric.printing_rate if body.process_type == "printing" else None
            )

        now = datetime.now(timezone.utc)
        entry = FabricProcessingEntry(
            production_lot_id=lot_id, process_type=body.process_type, vendor_id=body.vendor_id,
            in_date=body.in_date, input_kg=body.input_kg, rate_per_kg=rate_per_kg,
            notes=body.notes, created_at=now, created_by=user_id,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def complete_fabric_processing(
        self, entry_id: UUID, body: FabricProcessingComplete, company_id: UUID,
    ) -> FabricProcessingEntry | None:
        result = await self.db.execute(
            select(FabricProcessingEntry)
            .join(ProductionLot, ProductionLot.id == FabricProcessingEntry.production_lot_id)
            .where(FabricProcessingEntry.id == entry_id, ProductionLot.company_id == company_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        # No OUT≤IN guard here, deliberately — §47.5: dyeing/printing can
        # legitimately GAIN weight (absorbed dye/moisture); a decrease is equally
        # valid (shrinkage/wastage). Both are simply recorded, never rejected.
        entry.out_date = body.out_date
        entry.output_kg = body.output_kg
        entry.gain_loss_kg = body.output_kg - entry.input_kg
        entry.bill_amount = body.bill_amount
        if body.notes is not None:
            entry.notes = body.notes
        entry.status = "completed"
        entry.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return entry

    async def update_fabric_processing(
        self, entry_id: UUID, body: FabricProcessingUpdate, company_id: UUID,
    ) -> FabricProcessingEntry | None:
        """Correct any field after the fact (§47.5 — a gain or loss is data to
        record accurately, not to lock in as soon as it's first entered).
        """
        result = await self.db.execute(
            select(FabricProcessingEntry)
            .join(ProductionLot, ProductionLot.id == FabricProcessingEntry.production_lot_id)
            .where(FabricProcessingEntry.id == entry_id, ProductionLot.company_id == company_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(entry, field, val)
        if entry.output_kg is not None:
            entry.gain_loss_kg = entry.output_kg - entry.input_kg
        entry.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return entry

    async def add_lot_additional_cost(
        self, lot_id: UUID, body: LotAdditionalCostCreate, company_id: UUID,
    ) -> LotAdditionalCost | None:
        lot = (await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
        )).scalar_one_or_none()
        if not lot:
            return None
        cost = LotAdditionalCost(
            production_lot_id=lot_id, cost_type=body.cost_type, description=body.description,
            planned_amount=body.planned_amount, actual_amount=body.actual_amount, basis=body.basis,
            party_vendor_id=body.party_vendor_id, notes=body.notes, created_at=datetime.now(timezone.utc),
        )
        self.db.add(cost)
        await self.db.flush()
        return cost

    async def delete_lot_additional_cost(self, cost_id: UUID, company_id: UUID) -> bool:
        cost = (await self.db.execute(
            select(LotAdditionalCost)
            .join(ProductionLot, ProductionLot.id == LotAdditionalCost.production_lot_id)
            .where(LotAdditionalCost.id == cost_id, ProductionLot.company_id == company_id)
        )).scalar_one_or_none()
        if not cost:
            return False
        await self.db.delete(cost)
        await self.db.flush()
        return True

    async def update_lot_additional_cost(
        self, cost_id: UUID, body: LotAdditionalCostUpdate, company_id: UUID,
    ) -> LotAdditionalCost | None:
        result = await self.db.execute(
            select(LotAdditionalCost)
            .join(ProductionLot, ProductionLot.id == LotAdditionalCost.production_lot_id)
            .where(LotAdditionalCost.id == cost_id, ProductionLot.company_id == company_id)
        )
        cost = result.scalar_one_or_none()
        if not cost:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(cost, field, val)
        cost.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return cost

    async def update_lot_trim_actual(
        self, trim_id: UUID, body: LotTrimActualUpdate, company_id: UUID,
    ) -> LotTrim | None:
        result = await self.db.execute(
            select(LotTrim)
            .join(ProductionLot, ProductionLot.id == LotTrim.production_lot_id)
            .where(LotTrim.id == trim_id, ProductionLot.company_id == company_id)
        )
        trim = result.scalar_one_or_none()
        if not trim:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(trim, field, val)
        await self.db.flush()
        return trim

    async def update_lot_fabric_actual(
        self, fabric_id: UUID, body: LotFabricActualUpdate, company_id: UUID,
    ) -> LotFabric | None:
        result = await self.db.execute(
            select(LotFabric)
            .join(ProductionLot, ProductionLot.id == LotFabric.production_lot_id)
            .where(LotFabric.id == fabric_id, ProductionLot.company_id == company_id)
        )
        fabric = result.scalar_one_or_none()
        if not fabric:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(fabric, field, val)
        await self.db.flush()
        return fabric

    async def update_lot_yarn_actual(
        self, yarn_id: UUID, body: LotYarnActualUpdate, company_id: UUID,
    ) -> LotYarn | None:
        result = await self.db.execute(
            select(LotYarn)
            .join(ProductionLot, ProductionLot.id == LotYarn.production_lot_id)
            .where(LotYarn.id == yarn_id, ProductionLot.company_id == company_id)
        )
        yarn = result.scalar_one_or_none()
        if not yarn:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(yarn, field, val)
        await self.db.flush()
        return yarn

    async def update_lot_packing_actual(
        self, packing_id: UUID, body: LotPackingActualUpdate, company_id: UUID,
    ) -> LotPackingMaterial | None:
        result = await self.db.execute(
            select(LotPackingMaterial)
            .join(ProductionLot, ProductionLot.id == LotPackingMaterial.production_lot_id)
            .where(LotPackingMaterial.id == packing_id, ProductionLot.company_id == company_id)
        )
        packing = result.scalar_one_or_none()
        if not packing:
            return None
        for field, val in body.model_dump(exclude_unset=True).items():
            setattr(packing, field, val)
        await self.db.flush()
        return packing

    # ── Material Issues (MIS) ──────────────────────────────────────────────

    async def list_mis(
        self, company_id: UUID, lot_id: UUID | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[MaterialIssue], int]:
        q = (
            select(MaterialIssue)
            .where(MaterialIssue.company_id == company_id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        if lot_id:
            q = q.where(MaterialIssue.production_lot_id == lot_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(MaterialIssue.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_mis(self, mis_id: UUID, company_id: UUID) -> MaterialIssue | None:
        result = await self.db.execute(
            select(MaterialIssue)
            .where(MaterialIssue.id == mis_id, MaterialIssue.company_id == company_id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        return result.scalar_one_or_none()

    async def _accumulate_material_actual(self, production_lot_id: UUID, batch_lot_id: UUID, quantity: Decimal) -> None:
        """Adds `quantity` to the actual_qty of whichever LotFabric/LotYarn/
        LotTrim row (on this production lot) was planned against the
        specific inventory batch `batch_lot_id` — a no-op when nothing was
        planned against that exact batch (most issues, since planning
        against a specific received lot is the exception, not the rule)."""
        for lot_model, style_model in ((LotFabric, StyleFabric), (LotYarn, StyleYarn), (LotTrim, StyleTrim)):
            style_fk = "style_fabric_id" if style_model is StyleFabric else ("style_yarn_id" if style_model is StyleYarn else "style_trim_id")
            await self.db.execute(
                update(lot_model)
                .where(
                    getattr(lot_model, "production_lot_id") == production_lot_id,
                    getattr(lot_model, style_fk).in_(
                        select(style_model.id).where(style_model.lot_id == batch_lot_id)
                    ),
                )
                .values(actual_qty=func.coalesce(getattr(lot_model, "actual_qty"), 0) + quantity)
            )

    async def create_mis(self, body: MaterialIssueCreate, company_id: UUID, user_id: UUID) -> MaterialIssue:
        # Phase 8 — "do not allow stock to be issued twice through duplicate
        # requests or retries": the client resends the same idempotency_key
        # if a submission is retried (network blip, double-click before the
        # button disables). If an MIS with that key already exists, return
        # it unchanged instead of issuing the same stock a second time.
        if body.idempotency_key:
            existing = await self.db.execute(
                select(MaterialIssue)
                .where(MaterialIssue.company_id == company_id, MaterialIssue.idempotency_key == body.idempotency_key)
                .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        now = datetime.now(timezone.utc)
        issue_number = await _next_seq(self.db, "MIS", company_id, MaterialIssue)

        mis = MaterialIssue(
            company_id=company_id, issue_number=issue_number,
            production_lot_id=body.production_lot_id, stage_id=body.stage_id,
            warehouse_id=body.warehouse_id, issue_date=body.issue_date,
            idempotency_key=body.idempotency_key,
            notes=body.notes, created_by=user_id, created_at=now,
        )
        self.db.add(mis)
        await self.db.flush()

        for item_data in body.items:
            # FIFO costing (item #10): the client sends only quantity, not a
            # rate — each cost layer consumed becomes its own line so, e.g.,
            # issuing 15 when 10 were bought at ₹100 and 10 more at ₹200
            # produces two lines: 10 @ ₹100 and 5 @ ₹200, not one blended rate.
            inv_txns = await self.inv.issue_fifo(
                IssueParams(
                    company_id=company_id,
                    product_id=item_data.product_id,
                    variant_id=item_data.variant_id,
                    warehouse_id=body.warehouse_id,
                    quantity=item_data.issued_qty,
                    unit_id=item_data.unit_id,
                    unit_cost=Decimal("0"),
                    material_type="raw_material",
                    transaction_date=body.issue_date,
                    reference_type="material_issue",
                    reference_id=mis.id,
                    notes=f"MIS {issue_number}",
                ),
                user_id=user_id,
            )
            await self.db.flush()

            for i, inv_txn in enumerate(inv_txns):
                self.db.add(MaterialIssueItem(
                    material_issue_id=mis.id,
                    product_id=item_data.product_id,
                    variant_id=item_data.variant_id,
                    lot_id=inv_txn.lot_id,
                    planned_qty=item_data.planned_qty if i == 0 else None,
                    issued_qty=inv_txn.quantity,
                    unit_id=item_data.unit_id,
                    unit_cost=inv_txn.unit_cost,
                    total_cost=inv_txn.total_cost,
                    inv_transaction_id=inv_txn.id,
                ))
                # Material planning vs actual consumption (Phase 11): when the
                # consumed batch (inv_txn.lot_id) is the same specific batch a
                # StyleFabric/StyleYarn/StyleTrim row was planned against, roll
                # the issued quantity into that material's LOT-level
                # actual_qty automatically — no manual entry needed for the
                # common case of planning against a received batch.
                if inv_txn.lot_id is not None:
                    await self._accumulate_material_actual(body.production_lot_id, inv_txn.lot_id, inv_txn.quantity)

        await self.db.flush()

        result = await self.db.execute(
            select(MaterialIssue).where(MaterialIssue.id == mis.id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        return result.scalar_one()

    async def record_mis_item_return(
        self, item_id: UUID, body: MISItemReturnUpdate, company_id: UUID, user_id: UUID,
    ) -> MaterialIssueItem | None:
        """Records Used/Returned/Wastage against an issued material
        (spec §18/§19). A returned quantity flows back into real inventory
        via InventoryService.receive() - the same unified-inventory
        principle create_mis's issue() call already follows, just the
        inverse movement - which is what makes it "recoverable/resale"
        rather than a bare status flag.
        """
        result = await self.db.execute(
            select(MaterialIssueItem)
            .join(MaterialIssue, MaterialIssue.id == MaterialIssueItem.material_issue_id)
            .where(MaterialIssueItem.id == item_id, MaterialIssue.company_id == company_id)
            .options(selectinload(MaterialIssueItem.material_issue))
        )
        item = result.scalar_one_or_none()
        if not item:
            return None

        used = body.used_qty if body.used_qty is not None else item.used_qty
        returned = body.returned_qty if body.returned_qty is not None else item.returned_qty
        wastage = body.wastage_qty if body.wastage_qty is not None else item.wastage_qty
        total = (used or Decimal("0")) + (returned or Decimal("0")) + (wastage or Decimal("0"))
        if total > item.issued_qty:
            raise QuantityValidationError(
                f"Used + Returned + Wastage ({total}) cannot exceed the issued quantity ({item.issued_qty})"
            )

        previous_returned = item.returned_qty or Decimal("0")
        delta = (returned or Decimal("0")) - previous_returned
        if delta > 0:
            mis = item.material_issue
            inv_txn = await self.inv.receive(
                ReceiveParams(
                    company_id=company_id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    warehouse_id=mis.warehouse_id,
                    quantity=delta,
                    unit_id=item.unit_id,
                    unit_cost=item.unit_cost,
                    material_type="raw_material",
                    transaction_date=datetime.now(timezone.utc).date(),
                    reference_type="mis_return",
                    reference_id=item.id,
                    notes=f"Return against MIS {mis.issue_number}",
                ),
                user_id=user_id,
            )
            await self.db.flush()
            item.return_inv_transaction_id = inv_txn.id

        item.used_qty = used
        item.returned_qty = returned
        item.wastage_qty = wastage
        if body.notes is not None:
            item.return_notes = body.notes
        await self.db.flush()
        return item

    # ── Production Output (FG receive) ─────────────────────────────────────

    async def list_outputs(
        self, company_id: UUID, lot_id: UUID | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[ProductionOutput], int]:
        q = (
            select(ProductionOutput)
            .where(ProductionOutput.company_id == company_id)
            .options(selectinload(ProductionOutput.production_lot))
        )
        if lot_id:
            q = q.where(ProductionOutput.production_lot_id == lot_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(ProductionOutput.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_output(self, output_id: UUID, company_id: UUID) -> ProductionOutput | None:
        result = await self.db.execute(
            select(ProductionOutput)
            .where(ProductionOutput.id == output_id, ProductionOutput.company_id == company_id)
            .options(selectinload(ProductionOutput.production_lot))
        )
        return result.scalar_one_or_none()

    async def create_output(
        self, body: ProductionOutputCreate, company_id: UUID, user_id: UUID,
    ) -> ProductionOutput:
        now = datetime.now(timezone.utc)
        output_number = await _next_seq(self.db, "OUT", company_id, ProductionOutput)
        total_cost = (body.quantity * body.unit_cost).quantize(Decimal("0.01"))

        # Output row created first (flushed for its id) so the inventory
        # receipt can carry reference_id=output.id — previously this was left
        # None, meaning a finished-goods stock-in could never be traced back
        # to the production lot/output that created it (Phase 11 —
        # order-to-production traceability / dispatch reconciliation both
        # need this link).
        output = ProductionOutput(
            company_id=company_id, output_number=output_number,
            production_lot_id=body.production_lot_id, warehouse_id=body.warehouse_id,
            output_date=body.output_date, product_id=body.product_id, variant_id=body.variant_id,
            quantity=body.quantity, rejected_qty=body.rejected_qty, unit_id=body.unit_id,
            unit_cost=body.unit_cost, total_cost=total_cost,
            created_by=user_id, created_at=now,
        )
        self.db.add(output)
        await self.db.flush()

        inv_txn = await self.inv.receive(
            ReceiveParams(
                company_id=company_id,
                product_id=body.product_id,
                variant_id=body.variant_id,
                warehouse_id=body.warehouse_id,
                quantity=body.quantity,
                unit_id=body.unit_id,
                unit_cost=body.unit_cost,
                material_type="finished_good",
                transaction_date=body.output_date,
                reference_type="production_output",
                reference_id=output.id,
                notes=f"OUT {output_number}",
            ),
            user_id=user_id,
        )
        output.inv_transaction_id = inv_txn.id
        await self.db.flush()

        # Update lot actual_qty
        lot_res = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == body.production_lot_id)
        )
        lot = lot_res.scalar_one_or_none()
        if lot:
            lot.actual_qty += int(body.quantity)
            lot.updated_at = now

        await self.db.flush()

        # Sync the produced Product's cost_price to actual production cost
        # per saleable piece — recorded output changes both first_quality_qty
        # and, at the margin, the cost this output contributed, so the actual
        # cost/piece is worth re-syncing to Inventory on every output.
        if lot:
            full_lot = await self.get_lot(lot.id, company_id)
            if full_lot:
                cost_summary = compute_lot_cost_summary(full_lot)
                if cost_summary.cost_per_first_quality_piece is not None:
                    await self._sync_product_pricing(full_lot, cost_price=cost_summary.cost_per_first_quality_piece)
                    await self.db.flush()

        result = await self.db.execute(
            select(ProductionOutput).where(ProductionOutput.id == output.id)
            .options(selectinload(ProductionOutput.production_lot))
        )
        return result.scalar_one()

    # ── Mistake Log (16-item request #15) ──────────────────────────────────

    async def list_mistake_logs(self, lot_id: UUID, company_id: UUID) -> list[ProductionMistakeLog]:
        result = await self.db.execute(
            select(ProductionMistakeLog)
            .join(ProductionLot, ProductionMistakeLog.production_lot_id == ProductionLot.id)
            .where(ProductionMistakeLog.production_lot_id == lot_id, ProductionLot.company_id == company_id)
            .options(selectinload(ProductionMistakeLog.stage), selectinload(ProductionMistakeLog.staff))
            .order_by(ProductionMistakeLog.mistake_date.desc(), ProductionMistakeLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_mistake_log(
        self, lot_id: UUID, body: MistakeLogCreate, company_id: UUID, user_id: UUID,
    ) -> ProductionMistakeLog | None:
        lot = await self.db.execute(
            select(ProductionLot.id).where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
        )
        if not lot.scalar_one_or_none():
            return None
        log = ProductionMistakeLog(
            company_id=company_id, production_lot_id=lot_id,
            stage_id=body.stage_id, process_name=body.process_name,
            staff_id=body.staff_id, staff_name=body.staff_name,
            mistake_date=body.mistake_date, description=body.description,
            problem_type=body.problem_type, action_taken=body.action_taken,
            created_at=datetime.now(timezone.utc), created_by=user_id,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log, attribute_names=["stage", "staff"])
        return log

    async def delete_mistake_log(self, log_id: UUID, company_id: UUID) -> bool:
        result = await self.db.execute(
            select(ProductionMistakeLog)
            .join(ProductionLot, ProductionMistakeLog.production_lot_id == ProductionLot.id)
            .where(ProductionMistakeLog.id == log_id, ProductionLot.company_id == company_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            return False
        await self.db.delete(log)
        await self.db.flush()
        return True
