"""ProductionService: lots, stages, MIS, stage entries, FG output."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.master import Product
from app.models.production import (
    FabricProcessingEntry, InternalWorker, LotAdditionalCost, MaterialIssue, MaterialIssueItem,
    ProductionLot, ProductionLotSize, ProductionOutput,
    ProductionStage, ProductionStageChallan, ProductionStageEntry, Style, StyleAdditionalCost,
    StyleColour, StyleFabric, StylePackingMaterial, StyleProcess,
    StyleSize, StyleSubProcess, StyleTrim, StyleYarn,
)
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.inventory import IssueParams, ReceiveParams
from app.schemas.production import (
    FabricProcessingComplete, FabricProcessingCreate, FabricProcessingUpdate,
    InternalWorkerCreate,
    LotAdditionalCostCreate, LotAdditionalCostUpdate, LotCostComponentOut, LotCostSummaryOut,
    MaterialIssueCreate, MISItemCreate,
    ProductionLotCreate, ProductionLotUpdate,
    ProductionOutputCreate,
    StageChallanBillUpdate, StageChallanCreate, StageChallanReceive,
    StageCreate, StageEntryCreate, StageUpdate, StyleCreate,
    TargetPriceCheckOut, TargetPriceSuggestion,
)
from app.services.inventory import InventoryService


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

    is_final = lot.status in ("completed", "ready_to_dispatch")

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
            selectinload(Style.sizes),
            selectinload(Style.colours),
            selectinload(Style.yarns),
            selectinload(Style.fabrics),
            selectinload(Style.processes).selectinload(StyleProcess.sub_processes),
            selectinload(Style.trims),
            selectinload(Style.packing_materials),
            selectinload(Style.additional_costs),
        )

    async def get_style(self, style_id: UUID, company_id: UUID) -> Style | None:
        result = await self.db.execute(
            self._style_detail_query().where(Style.id == style_id, Style.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def create_style(self, body: StyleCreate, company_id: UUID, user_id: UUID) -> Style:
        """Create a Style Master: the complete production blueprint.

        Every section (sizes, colours, yarn, fabric, process workflow with
        sub-processes/tolerance/units/rates, trims, packing materials) is
        persisted in one transaction — see
        Garments_ERP_Style_Master_Specification.md §21.
        """
        now = datetime.now(timezone.utc)
        s = Style(
            company_id=company_id, created_at=now, created_by=user_id,
            name=body.name, code=body.code, description=body.description,
            garment_type=body.garment_type, gender=body.gender, season=body.season,
            final_output_unit=body.final_output_unit, target_price=body.target_price,
            pieces_per_box=body.pieces_per_box, fabric_source=body.fabric_source,
        )
        self.db.add(s)
        await self.db.flush()

        for sz in body.sizes:
            self.db.add(StyleSize(style_id=s.id, size_id=sz.size_id, sort_order=sz.sort_order, created_at=now))

        for cl in body.colours:
            self.db.add(StyleColour(style_id=s.id, colour_id=cl.colour_id, sort_order=cl.sort_order, created_at=now))

        for yn in body.yarns:
            self.db.add(StyleYarn(
                style_id=s.id, yarn_name=yn.yarn_name, lot_id=yn.lot_id,
                quantity=yn.quantity, unit=yn.unit, notes=yn.notes, created_at=now,
            ))

        for fb in body.fabrics:
            self.db.add(StyleFabric(
                style_id=s.id, fabric_name=fb.fabric_name, lot_id=fb.lot_id,
                consumption=fb.consumption, unit=fb.unit, excess_pct=fb.excess_pct,
                gsm=fb.gsm, dyeing_rate=fb.dyeing_rate, printing_rate=fb.printing_rate,
                notes=fb.notes, created_at=now,
            ))

        for proc in body.processes:
            p = StyleProcess(
                style_id=s.id, seq=proc.seq, process_name=proc.process_name,
                is_enabled=proc.is_enabled, tolerance_pct=proc.tolerance_pct,
                input_unit=proc.input_unit, output_unit=proc.output_unit,
                conversion_rule=proc.conversion_rule, min_rate=proc.min_rate,
                max_rate=proc.max_rate, planned_rate=proc.planned_rate,
                notes=proc.notes, created_at=now,
            )
            self.db.add(p)
            await self.db.flush()
            for sub in proc.sub_processes:
                self.db.add(StyleSubProcess(
                    style_process_id=p.id, seq=sub.seq, name=sub.name,
                    notes=sub.notes, created_at=now,
                ))

        for tr in body.trims:
            self.db.add(StyleTrim(
                style_id=s.id, trim_name=tr.trim_name, lot_id=tr.lot_id,
                quantity=tr.quantity, unit=tr.unit, category=tr.category,
                process_seq=tr.process_seq,
                excess_pct=tr.excess_pct, notes=tr.notes, created_at=now,
            ))

        for pm in body.packing_materials:
            self.db.add(StylePackingMaterial(
                style_id=s.id, material_name=pm.material_name, quantity=pm.quantity,
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
        return await self.get_style(s.id, company_id)

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

        payload = StyleCreate(
            name=f"{source.name} (Copy)", code=None, description=source.description,
            garment_type=source.garment_type, gender=source.gender, season=source.season,
            final_output_unit=source.final_output_unit, target_price=source.target_price,
            pieces_per_box=source.pieces_per_box, fabric_source=source.fabric_source,
            sizes=[{"size_id": x.size_id, "sort_order": x.sort_order} for x in source.sizes],
            colours=[{"colour_id": x.colour_id, "sort_order": x.sort_order} for x in source.colours],
            yarns=[{"yarn_name": x.yarn_name, "lot_id": x.lot_id, "quantity": x.quantity,
                     "unit": x.unit, "notes": x.notes} for x in source.yarns],
            fabrics=[{"fabric_name": x.fabric_name, "lot_id": x.lot_id, "consumption": x.consumption,
                       "unit": x.unit, "excess_pct": x.excess_pct, "gsm": x.gsm,
                       "dyeing_rate": x.dyeing_rate, "printing_rate": x.printing_rate, "notes": x.notes}
                      for x in source.fabrics],
            processes=[{
                "seq": p.seq, "process_name": p.process_name, "is_enabled": p.is_enabled,
                "tolerance_pct": p.tolerance_pct, "input_unit": p.input_unit, "output_unit": p.output_unit,
                "conversion_rule": p.conversion_rule, "min_rate": p.min_rate, "max_rate": p.max_rate,
                "planned_rate": p.planned_rate, "notes": p.notes,
                "sub_processes": [{"seq": sp.seq, "name": sp.name, "notes": sp.notes} for sp in p.sub_processes],
            } for p in source.processes],
            trims=[{"trim_name": x.trim_name, "lot_id": x.lot_id, "quantity": x.quantity, "unit": x.unit,
                     "category": x.category, "process_seq": x.process_seq, "excess_pct": x.excess_pct, "notes": x.notes} for x in source.trims],
            packing_materials=[{"material_name": x.material_name, "quantity": x.quantity, "unit": x.unit,
                                  "excess_pct": x.excess_pct, "consumption_stage": x.consumption_stage,
                                  "notes": x.notes} for x in source.packing_materials],
            additional_costs=[{"cost_type": x.cost_type, "description": x.description, "amount": x.amount,
                                 "basis": x.basis, "party_vendor_id": x.party_vendor_id, "notes": x.notes}
                                for x in source.additional_costs],
        )
        return await self.create_style(payload, company_id, user_id)

    async def update_style(self, style_id: UUID, body: StyleCreate, company_id: UUID) -> Style | None:
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
        s.updated_at = now

        await self.db.execute(delete(StyleSize).where(StyleSize.style_id == style_id))
        await self.db.execute(delete(StyleColour).where(StyleColour.style_id == style_id))
        await self.db.execute(delete(StyleYarn).where(StyleYarn.style_id == style_id))
        await self.db.execute(delete(StyleFabric).where(StyleFabric.style_id == style_id))
        await self.db.execute(delete(StyleProcess).where(StyleProcess.style_id == style_id))
        await self.db.execute(delete(StyleTrim).where(StyleTrim.style_id == style_id))
        await self.db.execute(delete(StylePackingMaterial).where(StylePackingMaterial.style_id == style_id))
        await self.db.execute(delete(StyleAdditionalCost).where(StyleAdditionalCost.style_id == style_id))
        await self.db.flush()

        for sz in body.sizes:
            self.db.add(StyleSize(style_id=style_id, size_id=sz.size_id, sort_order=sz.sort_order, created_at=now))

        for cl in body.colours:
            self.db.add(StyleColour(style_id=style_id, colour_id=cl.colour_id, sort_order=cl.sort_order, created_at=now))

        for yn in body.yarns:
            self.db.add(StyleYarn(
                style_id=style_id, yarn_name=yn.yarn_name, lot_id=yn.lot_id,
                quantity=yn.quantity, unit=yn.unit, notes=yn.notes, created_at=now,
            ))

        for fb in body.fabrics:
            self.db.add(StyleFabric(
                style_id=style_id, fabric_name=fb.fabric_name, lot_id=fb.lot_id,
                consumption=fb.consumption, unit=fb.unit, excess_pct=fb.excess_pct,
                gsm=fb.gsm, dyeing_rate=fb.dyeing_rate, printing_rate=fb.printing_rate,
                notes=fb.notes, created_at=now,
            ))

        for proc in body.processes:
            p = StyleProcess(
                style_id=style_id, seq=proc.seq, process_name=proc.process_name,
                is_enabled=proc.is_enabled, tolerance_pct=proc.tolerance_pct,
                input_unit=proc.input_unit, output_unit=proc.output_unit,
                conversion_rule=proc.conversion_rule, min_rate=proc.min_rate,
                max_rate=proc.max_rate, planned_rate=proc.planned_rate,
                notes=proc.notes, created_at=now,
            )
            self.db.add(p)
            await self.db.flush()
            for sub in proc.sub_processes:
                self.db.add(StyleSubProcess(
                    style_process_id=p.id, seq=sub.seq, name=sub.name,
                    notes=sub.notes, created_at=now,
                ))

        for tr in body.trims:
            self.db.add(StyleTrim(
                style_id=style_id, trim_name=tr.trim_name, lot_id=tr.lot_id,
                quantity=tr.quantity, unit=tr.unit, category=tr.category,
                process_seq=tr.process_seq,
                excess_pct=tr.excess_pct, notes=tr.notes, created_at=now,
            ))

        for pm in body.packing_materials:
            self.db.add(StylePackingMaterial(
                style_id=style_id, material_name=pm.material_name, quantity=pm.quantity,
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
        return await self.get_style(style_id, company_id)

    # ── Production Lots ────────────────────────────────────────────────────

    async def list_lots(
        self, company_id: UUID, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[ProductionLot], int]:
        q = (
            select(ProductionLot)
            .where(ProductionLot.company_id == company_id)
            .options(
                selectinload(ProductionLot.style).selectinload(Style.fabrics), selectinload(ProductionLot.sizes),
                selectinload(ProductionLot.stages).selectinload(ProductionStage.entries),
                selectinload(ProductionLot.stages).selectinload(ProductionStage.challans),
                selectinload(ProductionLot.additional_costs),
                selectinload(ProductionLot.fabric_processing),
                selectinload(ProductionLot.material_issues).selectinload(MaterialIssue.items),
                selectinload(ProductionLot.outputs),
            )
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
            .options(
                selectinload(ProductionLot.style).selectinload(Style.fabrics),
                selectinload(ProductionLot.sizes),
                selectinload(ProductionLot.stages).selectinload(ProductionStage.entries),
                selectinload(ProductionLot.stages).selectinload(ProductionStage.challans),
                selectinload(ProductionLot.additional_costs),
                selectinload(ProductionLot.fabric_processing),
                selectinload(ProductionLot.material_issues).selectinload(MaterialIssue.items),
                selectinload(ProductionLot.outputs),
            )
        )
        return result.scalar_one_or_none()

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

        for sz in body.sizes:
            self.db.add(ProductionLotSize(
                production_lot_id=lot.id, size_id=sz.size_id, planned_qty=sz.planned_qty,
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
        if style and style.processes:
            for i, proc in enumerate(sorted((p for p in style.processes if p.is_enabled), key=lambda p: p.seq)):
                stage_time = now + timedelta(milliseconds=i)
                self.db.add(ProductionStage(
                    production_lot_id=lot.id, style_process_id=proc.id,
                    stage_type=self._infer_stage_type(proc.process_name),
                    stage_name=proc.process_name, planned_qty=body.planned_qty if i == 0 else None,
                    tolerance_pct=proc.tolerance_pct, input_unit=proc.input_unit,
                    output_unit=proc.output_unit, conversion_rule=proc.conversion_rule,
                    min_rate=proc.min_rate, max_rate=proc.max_rate, planned_rate=proc.planned_rate,
                    created_at=stage_time, updated_at=stage_time,
                ))
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
                self.db.add(ProductionStage(
                    production_lot_id=lot.id, stage_type=stype, stage_name=sname,
                    planned_qty=body.planned_qty if i == 0 else None,
                    created_at=stage_time, updated_at=stage_time,
                ))

        await self.db.flush()
        result = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == lot.id)
            .options(selectinload(ProductionLot.style).selectinload(Style.fabrics), selectinload(ProductionLot.sizes),
                     selectinload(ProductionLot.stages).selectinload(ProductionStage.entries),
                     selectinload(ProductionLot.stages).selectinload(ProductionStage.challans),
                     selectinload(ProductionLot.additional_costs),
                     selectinload(ProductionLot.fabric_processing),
                     selectinload(ProductionLot.material_issues).selectinload(MaterialIssue.items),
                     selectinload(ProductionLot.outputs))
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

    async def advance_lot_status(self, lot_id: UUID, company_id: UUID, new_status: str) -> ProductionLot | None:
        valid_flow = {
            "draft": "planned", "planned": "approved",
            "approved": "in_production", "in_production": "qc",
            "qc": "packing", "packing": "ready_to_dispatch",
        }
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        if new_status not in valid_flow.values() and new_status not in ("cancelled", "completed"):
            return None
        lot.status = new_status
        lot.updated_at = datetime.now(timezone.utc)
        if new_status == "completed":
            lot.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return lot

    async def reopen_lot(self, lot_id: UUID, company_id: UUID) -> ProductionLot | None:
        """Reopen a cancelled/completed lot. Resumes at in_production when work
        was already recorded (stages, MIS, or output), otherwise back to draft.
        """
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        if lot.status not in ("cancelled", "completed"):
            raise ValueError(f"Only a cancelled or completed lot can be reopened (this one is {lot.status}).")
        has_activity = (
            lot.actual_qty > 0
            or bool(lot.material_issues)
            or bool(lot.outputs)
            or any(s.sent_qty > 0 or s.input_qty > 0 for s in lot.stages)
        )
        lot.status = "in_production" if has_activity else "draft"
        lot.closed_at = None
        lot.updated_at = datetime.now(timezone.utc)
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
            .options(selectinload(ProductionStage.entries), selectinload(ProductionStage.challans))
        )
        return result.scalar_one()

    async def add_stage_entry(
        self, stage_id: UUID, body: StageEntryCreate, user_id: UUID,
    ) -> ProductionStageEntry:
        now = datetime.now(timezone.utc)
        entry = ProductionStageEntry(
            stage_id=stage_id, entry_date=body.entry_date,
            pieces_in=body.pieces_in, pieces_out=body.pieces_out, rejected=body.rejected,
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
            stage.updated_at = now
            if stage.status == "pending" and body.pieces_in > 0:
                stage.status = "in_progress"
                stage.started_at = now
            if stage.rate_per_pc is not None or any(c.bill_amount for c in stage.challans):
                stage.bill_amount = _stage_actual_cost(stage)
            await self._propagate_to_next_stage(stage)

        await self.db.flush()
        return entry

    async def update_stage(self, stage_id: UUID, body: StageUpdate, company_id: UUID) -> ProductionStage | None:
        result = await self.db.execute(
            select(ProductionStage)
            .join(ProductionLot, ProductionLot.id == ProductionStage.production_lot_id)
            .where(ProductionStage.id == stage_id, ProductionLot.company_id == company_id)
            .options(selectinload(ProductionStage.entries), selectinload(ProductionStage.challans))
        )
        stage = result.scalar_one_or_none()
        if not stage:
            return None

        updates = body.model_dump(exclude_unset=True)
        # Validate any correction to sent/received/rejected as one consistent
        # set (§7 — editing a stage must not create impossible quantities):
        # received + rejected must never exceed sent.
        new_sent = updates.get("sent_qty", stage.sent_qty)
        new_received = updates.get("received_qty", stage.received_qty)
        new_rejected = updates.get("rejected_qty", stage.rejected_qty)
        if new_received + new_rejected > new_sent:
            raise QuantityValidationError(
                f"Received ({new_received}) + Rejected ({new_rejected}) cannot exceed Sent OUT ({new_sent})."
            )

        for field, val in updates.items():
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

    async def create_mis(self, body: MaterialIssueCreate, company_id: UUID, user_id: UUID) -> MaterialIssue:
        now = datetime.now(timezone.utc)
        issue_number = await _next_seq(self.db, "MIS", company_id, MaterialIssue)

        mis = MaterialIssue(
            company_id=company_id, issue_number=issue_number,
            production_lot_id=body.production_lot_id, stage_id=body.stage_id,
            warehouse_id=body.warehouse_id, issue_date=body.issue_date,
            notes=body.notes, created_by=user_id, created_at=now,
        )
        self.db.add(mis)
        await self.db.flush()

        for item_data in body.items:
            total_cost = (item_data.issued_qty * item_data.unit_cost).quantize(Decimal("0.01"))
            inv_txn = await self.inv.issue(
                IssueParams(
                    company_id=company_id,
                    product_id=item_data.product_id,
                    variant_id=item_data.variant_id,
                    warehouse_id=body.warehouse_id,
                    quantity=item_data.issued_qty,
                    unit_id=item_data.unit_id,
                    unit_cost=item_data.unit_cost,
                    material_type="raw_material",
                    transaction_date=body.issue_date,
                    reference_type="material_issue",
                    reference_id=mis.id,
                    notes=f"MIS {issue_number}",
                ),
                user_id=user_id,
            )
            await self.db.flush()

            self.db.add(MaterialIssueItem(
                material_issue_id=mis.id,
                product_id=item_data.product_id,
                variant_id=item_data.variant_id,
                planned_qty=item_data.planned_qty,
                issued_qty=item_data.issued_qty,
                unit_id=item_data.unit_id,
                unit_cost=item_data.unit_cost,
                total_cost=total_cost,
                inv_transaction_id=inv_txn.id,
            ))

        await self.db.flush()

        # Advance lot status to in_production if still at planned/approved
        lot_res = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == body.production_lot_id)
        )
        lot = lot_res.scalar_one_or_none()
        if lot and lot.status in ("draft", "planned", "approved", "material_pending"):
            lot.status = "in_production"
            lot.updated_at = now

        await self.db.flush()

        result = await self.db.execute(
            select(MaterialIssue).where(MaterialIssue.id == mis.id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        return result.scalar_one()

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

    async def create_output(
        self, body: ProductionOutputCreate, company_id: UUID, user_id: UUID,
    ) -> ProductionOutput:
        now = datetime.now(timezone.utc)
        output_number = await _next_seq(self.db, "OUT", company_id, ProductionOutput)
        total_cost = (body.quantity * body.unit_cost).quantize(Decimal("0.01"))

        inv_txn = await self.inv.receive(
            ReceiveParams(
                company_id=company_id,
                product_id=body.product_id,
                warehouse_id=body.warehouse_id,
                quantity=body.quantity,
                unit_id=body.unit_id,
                unit_cost=body.unit_cost,
                material_type="finished_good",
                transaction_date=body.output_date,
                reference_type="production_output",
                reference_id=None,
                notes=f"OUT {output_number}",
            ),
            user_id=user_id,
        )
        await self.db.flush()

        output = ProductionOutput(
            company_id=company_id, output_number=output_number,
            production_lot_id=body.production_lot_id, warehouse_id=body.warehouse_id,
            output_date=body.output_date, product_id=body.product_id,
            quantity=body.quantity, rejected_qty=body.rejected_qty, unit_id=body.unit_id,
            unit_cost=body.unit_cost, total_cost=total_cost,
            inv_transaction_id=inv_txn.id,
            created_by=user_id, created_at=now,
        )
        self.db.add(output)
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
