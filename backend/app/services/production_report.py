"""Production Lot PDF report — data assembly + rendering.

Reuses ProductionService.resolve_selling_prices() and compute_lot_cost_summary()
directly (the exact same functions the costing UI consumes via _lot_out() in
app/api/v1/endpoints/production.py) so the report can never disagree with the
application's own numbers — no calculation logic is duplicated here, only
presentation-shaping of already-computed data.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.models.company import Company
from app.models.master import Product
from app.models.production import InternalWorker, ProductionLot
from app.models.purchase import Vendor
from app.models.sales import Customer
from app.services.production import (
    ProductionService, _stage_accepted_qty, _stage_actual_cost, compute_lot_cost_summary,
)

_CENTS = Decimal("0.01")


def _inr(value, decimals: int = 0) -> str:
    """Indian digit-grouped currency, e.g. 1750000 -> '₹17,50,000', with
    optional decimal precision for per-piece figures (e.g. '₹44.67')."""
    if value is None:
        return "—"
    value = Decimal(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if decimals:
        value = value.quantize(Decimal(1).scaleb(-decimals))
        int_part, _, frac = f"{value:f}".partition(".")
    else:
        int_part, frac = str(int(value.quantize(Decimal(1)))), ""
    if len(int_part) > 3:
        last3, rest = int_part[-3:], int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups) + "," + last3
    result = f"₹{sign}{int_part}"
    return f"{result}.{frac}" if frac else result


def _qty(value) -> str:
    if value is None:
        return "—"
    value = Decimal(value)
    text = str(int(value)) if value == value.to_integral_value() else str(value.quantize(Decimal("0.01")))
    return f"{text} pcs"


def _pct(value) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):.2f}%"


_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
_env.filters["inr"] = _inr
_env.filters["qty"] = _qty
_env.filters["pct"] = _pct


async def build_lot_report_data(
    db: AsyncSession, svc: ProductionService, lot: ProductionLot, company_id: UUID,
) -> dict:
    """Assemble every value the report template needs. Pure presentation
    shaping over already-loaded `lot` relationships plus a handful of small
    batched lookups (company/customer/vendor/worker/product names) — no
    business calculation happens here beyond the two reused functions above.
    """
    selling_prices = await svc.resolve_selling_prices(lot)
    cost_summary = compute_lot_cost_summary(lot, selling_prices)

    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()

    customer = None
    if lot.customer_id:
        customer = (
            await db.execute(select(Customer).where(Customer.id == lot.customer_id))
        ).scalar_one_or_none()

    vendor_ids = {c.vendor_id for s in lot.stages for c in s.challans if c.vendor_id}
    worker_ids = {c.worker_id for s in lot.stages for c in s.challans if c.worker_id}
    vendor_by_id: dict[UUID, str] = {}
    if vendor_ids:
        for v in (await db.execute(select(Vendor).where(Vendor.id.in_(vendor_ids)))).scalars().all():
            vendor_by_id[v.id] = v.name
    worker_by_id: dict[UUID, str] = {}
    if worker_ids:
        for w in (await db.execute(select(InternalWorker).where(InternalWorker.id.in_(worker_ids)))).scalars().all():
            worker_by_id[w.id] = w.name

    product_ids = {o.product_id for o in lot.outputs} | {
        item.product_id for mis in lot.material_issues for item in mis.items
    }
    product_by_id: dict[UUID, str] = {}
    if product_ids:
        for p in (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all():
            product_by_id[p.id] = p.name

    output_products = sorted({product_by_id.get(o.product_id, "—") for o in lot.outputs})

    # ── Stage flow, assignment, and rejection tables (lot order) ──────────
    stage_rows: list[dict] = []
    assignment_rows: list[dict] = []
    rejection_rows: list[dict] = []
    for s in lot.stages:
        accepted = _stage_accepted_qty(s)
        is_assigned = bool(s.assignment_type)
        stage_rows.append({
            "name": s.stage_name, "assigned": is_assigned,
            "planned_qty": s.planned_qty,
            "sent_qty": s.sent_qty, "received_qty": s.received_qty,
            "input_qty": s.input_qty, "output_qty": s.output_qty,
            "rejected_qty": s.rejected_qty, "accepted_qty": accepted,
        })
        base_input = s.sent_qty if is_assigned else s.input_qty
        if base_input:
            rejection_rows.append({
                "name": s.stage_name, "input": base_input, "accepted": accepted,
                "rejected": s.rejected_qty,
                "rejection_pct": (Decimal(s.rejected_qty) / Decimal(base_input) * 100).quantize(_CENTS),
            })
        if s.challans:
            for c in s.challans:
                assignee = vendor_by_id.get(c.vendor_id) if c.vendor_id else worker_by_id.get(c.worker_id)
                # Prefer this challan's own invoiced bill (authoritative); when
                # it has none yet, estimate this challan's share of the
                # stage's rate-based cost from its own received qty — matches
                # _stage_actual_cost()'s rate-first priority without crediting
                # one challan with the whole stage's cost when a stage has
                # more than one challan.
                if c.bill_amount is not None:
                    challan_cost = c.bill_amount
                elif s.rate_per_pc is not None and c.in_qty is not None:
                    challan_cost = (s.rate_per_pc * c.in_qty).quantize(Decimal("0.01"))
                else:
                    challan_cost = None
                assignment_rows.append({
                    "stage": s.stage_name, "assignment_type": s.assignment_type,
                    "assignee": assignee or "—", "challan_number": c.challan_number,
                    "out_qty": c.out_qty, "in_qty": c.in_qty, "rejected_qty": c.rejected_qty,
                    "rate": s.rate_per_pc, "actual_cost": challan_cost,
                    "is_vendor": c.vendor_id is not None,
                    "bill_status": "Received" if c.bill_received else ("Invoiced" if c.bill_amount is not None else "Pending"),
                })
        elif accepted > 0 or s.rejected_qty > 0:
            assignment_rows.append({
                "stage": s.stage_name, "assignment_type": s.assignment_type,
                "assignee": "In-house", "challan_number": None,
                "out_qty": None, "in_qty": None, "rejected_qty": s.rejected_qty,
                "rate": s.rate_per_pc, "actual_cost": _stage_actual_cost(s) or None,
                "is_vendor": False, "bill_status": None,
            })

    # ── Material / fabric detail ───────────────────────────────────────────
    material_rows = [
        {
            "product_name": product_by_id.get(item.product_id, "—"),
            "issue_number": mis.issue_number,
            "issued_qty": item.issued_qty, "unit_cost": item.unit_cost, "total_cost": item.total_cost,
        }
        for mis in lot.material_issues for item in mis.items
    ]

    additional_cost_rows = [a for a in lot.additional_costs if a.cost_type == "additional"]
    agent_commission_rows = [a for a in lot.additional_costs if a.cost_type == "agent_commission"]

    cost_per_piece_rows = []
    if cost_summary.first_quality_qty > 0:
        for comp in cost_summary.components:
            if comp.actual_amount is not None:
                cost_per_piece_rows.append({
                    "name": comp.name,
                    "per_piece": (comp.actual_amount / cost_summary.first_quality_qty).quantize(_CENTS),
                })

    return {
        "company": company,
        "lot": lot,
        "customer": customer,
        "output_products": output_products,
        "cost_summary": cost_summary,
        "stage_rows": stage_rows,
        "assignment_rows": assignment_rows,
        "rejection_rows": rejection_rows,
        "material_rows": material_rows,
        "additional_cost_rows": additional_cost_rows,
        "agent_commission_rows": agent_commission_rows,
        "cost_per_piece_rows": cost_per_piece_rows,
        "show_planned_vs_actual": cost_summary.target_price is not None and cost_summary.target_revenue is not None,
        "is_final": cost_summary.is_final,
        "generated_at": datetime.now(timezone.utc),
    }


def render_lot_report_pdf(report_data: dict) -> bytes:
    template = _env.get_template("production_report.html")
    html = template.render(**report_data)
    return HTML(string=html).write_pdf()


def report_filename(lot: ProductionLot, style_name: str | None) -> str:
    def _safe(s: str) -> str:
        return "".join(c if (c.isalnum() or c in ("-", "_")) else "-" for c in s).strip("-")
    parts = ["Production_Report", _safe(lot.lot_number)]
    if style_name:
        parts.append(_safe(style_name))
    return "_".join(parts) + ".pdf"
