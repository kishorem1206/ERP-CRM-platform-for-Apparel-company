"""ReportsService: aggregated read-only queries for all report pages."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import Customer


class ReportsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Sales Summary ─────────────────────────────────────────────────────────

    async def sales_summary(
        self, company_id: UUID, from_date: date, to_date: date,
    ) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT
                    c.legal_name            AS customer_name,
                    c.customer_type,
                    COUNT(i.id)             AS invoice_count,
                    SUM(i.taxable_amount)   AS taxable_amount,
                    SUM(i.cgst_amount)      AS cgst_amount,
                    SUM(i.sgst_amount)      AS sgst_amount,
                    SUM(i.igst_amount)      AS igst_amount,
                    SUM(i.total_amount)     AS total_amount,
                    SUM(i.paid_amount)      AS paid_amount,
                    SUM(i.balance_amount)   AS outstanding
                FROM invoices i
                JOIN customers c ON c.id = i.customer_id
                WHERE i.company_id   = :cid
                  AND i.invoice_date BETWEEN :fd AND :td
                GROUP BY c.id, c.legal_name, c.customer_type
                ORDER BY total_amount DESC
            """),
            {"cid": str(company_id), "fd": from_date, "td": to_date},
        )
        return [dict(r._mapping) for r in result]

    # ── Purchase Summary ──────────────────────────────────────────────────────

    async def purchase_summary(
        self, company_id: UUID, from_date: date, to_date: date,
    ) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT
                    v.name                  AS vendor_name,
                    v.vendor_type,
                    COUNT(pe.id)            AS entry_count,
                    SUM(pe.taxable_amount)  AS taxable_amount,
                    SUM(pe.cgst_amount)     AS cgst_amount,
                    SUM(pe.sgst_amount)     AS sgst_amount,
                    SUM(pe.igst_amount)     AS igst_amount,
                    SUM(pe.total_amount)    AS total_amount,
                    SUM(pe.paid_amount)     AS paid_amount,
                    SUM(pe.balance_amount)  AS outstanding
                FROM purchase_entries pe
                JOIN vendors v ON v.id = pe.vendor_id
                WHERE pe.company_id  = :cid
                  AND pe.entry_date  BETWEEN :fd AND :td
                GROUP BY v.id, v.name, v.vendor_type
                ORDER BY total_amount DESC
            """),
            {"cid": str(company_id), "fd": from_date, "td": to_date},
        )
        return [dict(r._mapping) for r in result]

    # ── Production Efficiency ─────────────────────────────────────────────────

    async def production_efficiency(self, company_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT
                    pl.lot_number,
                    COALESCE(s.name, '—')   AS style_name,
                    pl.planned_qty,
                    pl.actual_qty,
                    pl.status,
                    pl.delivery_date,
                    pl.created_at::date     AS lot_date,
                    CASE
                        WHEN pl.planned_qty > 0
                        THEN ROUND((pl.actual_qty::numeric / pl.planned_qty) * 100, 1)
                        ELSE 0
                    END                     AS efficiency_pct,
                    (pl.actual_qty - pl.planned_qty) AS variance
                FROM production_lots pl
                LEFT JOIN styles s ON s.id = pl.style_id
                WHERE pl.company_id = :cid
                ORDER BY pl.created_at DESC
            """),
            {"cid": str(company_id)},
        )
        return [dict(r._mapping) for r in result]

    # ── GST Summary (monthly) ─────────────────────────────────────────────────

    async def gst_summary(
        self, company_id: UUID, from_date: date, to_date: date,
    ) -> dict:
        output_res = await self.db.execute(
            text("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', invoice_date), 'YYYY-MM') AS month,
                    SUM(taxable_amount)  AS taxable_amount,
                    SUM(cgst_amount)     AS cgst_amount,
                    SUM(sgst_amount)     AS sgst_amount,
                    SUM(igst_amount)     AS igst_amount,
                    SUM(total_amount)    AS total_amount,
                    COUNT(id)            AS invoice_count
                FROM invoices
                WHERE company_id   = :cid
                  AND invoice_date BETWEEN :fd AND :td
                GROUP BY DATE_TRUNC('month', invoice_date)
                ORDER BY month DESC
            """),
            {"cid": str(company_id), "fd": from_date, "td": to_date},
        )
        input_res = await self.db.execute(
            text("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', entry_date), 'YYYY-MM') AS month,
                    SUM(taxable_amount)  AS taxable_amount,
                    SUM(cgst_amount)     AS cgst_amount,
                    SUM(sgst_amount)     AS sgst_amount,
                    SUM(igst_amount)     AS igst_amount,
                    SUM(total_amount)    AS total_amount,
                    COUNT(id)            AS entry_count
                FROM purchase_entries
                WHERE company_id = :cid
                  AND entry_date BETWEEN :fd AND :td
                GROUP BY DATE_TRUNC('month', entry_date)
                ORDER BY month DESC
            """),
            {"cid": str(company_id), "fd": from_date, "td": to_date},
        )
        return {
            "output": [dict(r._mapping) for r in output_res],
            "input": [dict(r._mapping) for r in input_res],
        }

    # ── Stock Ageing ──────────────────────────────────────────────────────────

    async def stock_ageing(self, company_id: UUID, as_of: date | None = None) -> list[dict]:
        """Age is computed per (product, warehouse, lot) when a transaction
        carries a lot_id, instead of only ever using the single
        earliest-ever receipt date for the whole product+warehouse — two
        batches of the same product sitting in the same warehouse now age
        independently. Transactions with no lot_id (most pre-Phase-10 data)
        fall back to the old product+warehouse grouping unchanged.
        `corrected_date` (Phase 10 manual correction) is preferred over the
        raw `transaction_date` wherever it's been set; `as_of` lets the
        caller report age as of a date other than today."""
        as_of = as_of or date.today()
        result = await self.db.execute(
            text("""
                WITH stock_balance AS (
                    SELECT
                        it.product_id,
                        it.warehouse_id,
                        it.lot_id,
                        it.unit_id,
                        SUM(it.quantity * it.direction) AS balance
                    FROM inventory_transactions it
                    WHERE it.company_id = :cid
                    GROUP BY it.product_id, it.warehouse_id, it.lot_id, it.unit_id
                    HAVING SUM(it.quantity * it.direction) > 0
                ),
                earliest_receipt AS (
                    SELECT
                        product_id,
                        warehouse_id,
                        lot_id,
                        MIN(COALESCE(corrected_date, transaction_date)) AS first_date
                    FROM inventory_transactions
                    WHERE company_id = :cid AND direction = 1
                    GROUP BY product_id, warehouse_id, lot_id
                ),
                avg_cost AS (
                    SELECT
                        product_id,
                        warehouse_id,
                        lot_id,
                        SUM(quantity * unit_cost) / NULLIF(SUM(quantity), 0) AS wavg_cost
                    FROM inventory_transactions
                    WHERE company_id = :cid AND direction = 1
                    GROUP BY product_id, warehouse_id, lot_id
                )
                SELECT
                    p.name              AS product_name,
                    p.product_type,
                    w.name              AS warehouse_name,
                    u.abbreviation      AS unit_symbol,
                    il.lot_number       AS lot_number,
                    sb.balance,
                    ROUND(sb.balance * COALESCE(ac.wavg_cost, 0), 2) AS stock_value,
                    er.first_date       AS oldest_receipt_date,
                    (CAST(:as_of AS DATE) - er.first_date) AS age_days,
                    CASE
                        WHEN (CAST(:as_of AS DATE) - er.first_date) <= 30  THEN '0-30 days'
                        WHEN (CAST(:as_of AS DATE) - er.first_date) <= 60  THEN '31-60 days'
                        WHEN (CAST(:as_of AS DATE) - er.first_date) <= 90  THEN '61-90 days'
                        ELSE '90+ days'
                    END                 AS age_bucket
                FROM stock_balance sb
                JOIN products   p ON p.id = sb.product_id
                JOIN warehouses w ON w.id = sb.warehouse_id
                JOIN units      u ON u.id = sb.unit_id
                LEFT JOIN inventory_lots il ON il.id = sb.lot_id
                LEFT JOIN earliest_receipt er
                    ON er.product_id   = sb.product_id
                    AND er.warehouse_id = sb.warehouse_id
                    AND (er.lot_id = sb.lot_id OR (er.lot_id IS NULL AND sb.lot_id IS NULL))
                LEFT JOIN avg_cost ac
                    ON ac.product_id   = sb.product_id
                    AND ac.warehouse_id = sb.warehouse_id
                    AND (ac.lot_id = sb.lot_id OR (ac.lot_id IS NULL AND sb.lot_id IS NULL))
                ORDER BY age_days DESC NULLS LAST
            """),
            {"cid": str(company_id), "as_of": as_of},
        )
        return [dict(r._mapping) for r in result]

    # ── Invoice Register & AR Ageing ──────────────────────────────────────────

    async def invoice_register(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        clauses = ["i.company_id = :cid", "i.invoice_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if customer_id:
            clauses.append("i.customer_id = :cust")
            params["cust"] = str(customer_id)
        if status:
            clauses.append("i.status = :status")
            params["status"] = status
        result = await self.db.execute(
            text(f"""
                SELECT
                    i.invoice_number, c.legal_name AS customer_name, i.invoice_date, i.due_date,
                    i.status, i.total_amount, i.paid_amount, i.balance_amount,
                    (CURRENT_DATE - COALESCE(i.due_date, i.invoice_date)) AS age_days,
                    CASE
                        WHEN i.balance_amount <= 0 THEN 'Paid'
                        WHEN (CURRENT_DATE - COALESCE(i.due_date, i.invoice_date)) <= 30 THEN '0-30 days'
                        WHEN (CURRENT_DATE - COALESCE(i.due_date, i.invoice_date)) <= 60 THEN '31-60 days'
                        WHEN (CURRENT_DATE - COALESCE(i.due_date, i.invoice_date)) <= 90 THEN '61-90 days'
                        ELSE '90+ days'
                    END AS age_bucket
                FROM invoices i
                JOIN customers c ON c.id = i.customer_id
                WHERE {" AND ".join(clauses)}
                ORDER BY i.invoice_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Quotation Register ────────────────────────────────────────────────────

    async def quotation_register(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        clauses = ["q.company_id = :cid", "q.quotation_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if customer_id:
            clauses.append("q.customer_id = :cust")
            params["cust"] = str(customer_id)
        if status:
            clauses.append("q.status = :status")
            params["status"] = status
        result = await self.db.execute(
            text(f"""
                SELECT
                    q.quotation_number, c.legal_name AS customer_name, q.quotation_date,
                    q.valid_until, q.status, q.total_amount, so.order_number AS converted_order_number
                FROM quotations q
                JOIN customers c ON c.id = q.customer_id
                LEFT JOIN sales_orders so ON so.id = q.converted_order_id
                WHERE {" AND ".join(clauses)}
                ORDER BY q.quotation_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Sales Order Book ──────────────────────────────────────────────────────

    async def sales_order_book(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        clauses = ["so.company_id = :cid", "so.order_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if customer_id:
            clauses.append("so.customer_id = :cust")
            params["cust"] = str(customer_id)
        if status:
            clauses.append("so.status = :status")
            params["status"] = status
        result = await self.db.execute(
            text(f"""
                SELECT
                    so.order_number, c.legal_name AS customer_name, so.order_date,
                    so.expected_delivery, so.status, so.total_amount,
                    COALESCE(SUM(soi.quantity), 0)      AS ordered_qty,
                    COALESCE(SUM(soi.delivered_qty), 0) AS delivered_qty,
                    CASE
                        WHEN SUM(soi.quantity) > 0
                        THEN ROUND(SUM(soi.delivered_qty) / SUM(soi.quantity) * 100, 1)
                        ELSE 0
                    END AS fulfilment_pct
                FROM sales_orders so
                JOIN customers c ON c.id = so.customer_id
                LEFT JOIN sales_order_items soi ON soi.sales_order_id = so.id
                WHERE {" AND ".join(clauses)}
                GROUP BY so.id, so.order_number, c.legal_name, so.order_date,
                         so.expected_delivery, so.status, so.total_amount
                ORDER BY so.order_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Sales by Product ──────────────────────────────────────────────────────

    async def sales_by_product(
        self, company_id: UUID, from_date: date, to_date: date,
        product_id: UUID | None = None, category_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["so.company_id = :cid", "so.order_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if product_id:
            clauses.append("soi.product_id = :pid")
            params["pid"] = str(product_id)
        if category_id:
            clauses.append("p.category_id = :catid")
            params["catid"] = str(category_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    p.name AS product_name, p.code AS product_code, cat.name AS category_name,
                    SUM(soi.quantity)      AS qty_ordered,
                    SUM(soi.total_amount)  AS revenue,
                    COUNT(DISTINCT so.id)  AS order_count
                FROM sales_order_items soi
                JOIN sales_orders so ON so.id = soi.sales_order_id
                JOIN products p ON p.id = soi.product_id
                LEFT JOIN categories cat ON cat.id = p.category_id
                WHERE {" AND ".join(clauses)}
                GROUP BY p.id, p.name, p.code, cat.name
                ORDER BY revenue DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Purchase Order Register ───────────────────────────────────────────────

    async def po_register(
        self, company_id: UUID, from_date: date, to_date: date,
        vendor_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        clauses = ["po.company_id = :cid", "po.order_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if vendor_id:
            clauses.append("po.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        if status:
            clauses.append("po.status = :status")
            params["status"] = status
        result = await self.db.execute(
            text(f"""
                SELECT
                    po.po_number, v.name AS vendor_name, po.order_date, po.expected_date,
                    po.status, po.total_amount,
                    COALESCE(SUM(poi.ordered_qty), 0)  AS ordered_qty,
                    COALESCE(SUM(poi.received_qty), 0) AS received_qty,
                    CASE
                        WHEN SUM(poi.ordered_qty) > 0
                        THEN ROUND(SUM(poi.received_qty) / SUM(poi.ordered_qty) * 100, 1)
                        ELSE 0
                    END AS received_pct
                FROM purchase_orders po
                JOIN vendors v ON v.id = po.vendor_id
                LEFT JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
                WHERE {" AND ".join(clauses)}
                GROUP BY po.id, po.po_number, v.name, po.order_date, po.expected_date,
                         po.status, po.total_amount
                ORDER BY po.order_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── GRN Register ──────────────────────────────────────────────────────────

    async def grn_register(
        self, company_id: UUID, from_date: date, to_date: date,
        vendor_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        clauses = ["pe.company_id = :cid", "pe.entry_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if vendor_id:
            clauses.append("pe.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        if status:
            clauses.append("pe.status = :status")
            params["status"] = status
        result = await self.db.execute(
            text(f"""
                SELECT
                    pe.entry_number, v.name AS vendor_name, pe.entry_date, pe.status,
                    pe.payment_status, pe.total_amount, pe.paid_amount, pe.balance_amount,
                    COALESCE(SUM(pei.received_qty), 0) AS received_qty,
                    COALESCE(SUM(pei.accepted_qty), 0) AS accepted_qty,
                    COALESCE(SUM(pei.rejected_qty), 0) AS rejected_qty
                FROM purchase_entries pe
                JOIN vendors v ON v.id = pe.vendor_id
                LEFT JOIN purchase_entry_items pei ON pei.purchase_entry_id = pe.id
                WHERE {" AND ".join(clauses)}
                GROUP BY pe.id, pe.entry_number, v.name, pe.entry_date, pe.status,
                         pe.payment_status, pe.total_amount, pe.paid_amount, pe.balance_amount
                ORDER BY pe.entry_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Vendor Payable Ageing ─────────────────────────────────────────────────

    async def vendor_payable_ageing(
        self, company_id: UUID, vendor_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["pe.company_id = :cid", "pe.balance_amount > 0"]
        params: dict = {"cid": str(company_id)}
        if vendor_id:
            clauses.append("pe.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    v.name AS vendor_name, pe.entry_number, pe.entry_date,
                    pe.total_amount, pe.balance_amount,
                    (CURRENT_DATE - pe.entry_date) AS age_days,
                    CASE
                        WHEN (CURRENT_DATE - pe.entry_date) <= 30 THEN '0-30 days'
                        WHEN (CURRENT_DATE - pe.entry_date) <= 60 THEN '31-60 days'
                        WHEN (CURRENT_DATE - pe.entry_date) <= 90 THEN '61-90 days'
                        ELSE '90+ days'
                    END AS age_bucket
                FROM purchase_entries pe
                JOIN vendors v ON v.id = pe.vendor_id
                WHERE {" AND ".join(clauses)}
                ORDER BY age_days DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Stock Summary (current balance) ──────────────────────────────────────

    async def stock_summary(
        self, company_id: UUID, warehouse_id: UUID | None = None,
        category_id: UUID | None = None, product_type: str | None = None,
    ) -> list[dict]:
        clauses = ["it.company_id = :cid"]
        params: dict = {"cid": str(company_id)}
        if warehouse_id:
            clauses.append("it.warehouse_id = :wid")
            params["wid"] = str(warehouse_id)
        if category_id:
            clauses.append("p.category_id = :catid")
            params["catid"] = str(category_id)
        if product_type:
            clauses.append("p.product_type = :ptype")
            params["ptype"] = product_type
        result = await self.db.execute(
            text(f"""
                SELECT
                    p.name AS product_name, p.code AS product_code, p.product_type,
                    cat.name AS category_name, w.name AS warehouse_name, u.abbreviation AS unit_symbol,
                    SUM(it.quantity * it.direction) AS balance,
                    ROUND(SUM(it.quantity * it.direction) * COALESCE(p.cost_price, 0), 2) AS stock_value
                FROM inventory_transactions it
                JOIN products p   ON p.id = it.product_id
                JOIN warehouses w ON w.id = it.warehouse_id
                JOIN units u      ON u.id = it.unit_id
                LEFT JOIN categories cat ON cat.id = p.category_id
                WHERE {" AND ".join(clauses)}
                GROUP BY p.id, p.name, p.code, p.product_type, cat.name, w.id, w.name, u.abbreviation
                HAVING SUM(it.quantity * it.direction) <> 0
                ORDER BY p.name
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Material Lot Register ────────────────────────────────────────────────

    async def material_lot_register(
        self, company_id: UUID, from_date: date, to_date: date,
        material_type: str | None = None,
    ) -> list[dict]:
        clauses = ["il.company_id = :cid", "il.created_at::date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if material_type:
            clauses.append("il.material_type = :mtype")
            params["mtype"] = material_type
        result = await self.db.execute(
            text(f"""
                SELECT
                    il.lot_number, il.material_type, COALESCE(v.name, '—') AS supplier_name,
                    il.invoice_number, il.invoice_date, il.unit_cost, il.created_at::date AS lot_date,
                    COALESCE(SUM(it.quantity) FILTER (WHERE it.direction = 1), 0) AS received_qty,
                    MAX(u.abbreviation) AS unit_symbol
                FROM inventory_lots il
                LEFT JOIN vendors v ON v.id = il.supplier_id
                LEFT JOIN inventory_transactions it ON it.lot_id = il.id
                LEFT JOIN units u ON u.id = it.unit_id
                WHERE {" AND ".join(clauses)}
                GROUP BY il.id, il.lot_number, il.material_type, v.name,
                         il.invoice_number, il.invoice_date, il.unit_cost, il.created_at
                ORDER BY il.created_at DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Lot Costing Register (reuses the exact costing engine) ──────────────
    # The one report backed by ORM + compute_lot_cost_summary() instead of raw
    # SQL — it must never recompute costing logic, only read it.

    async def lot_costing_register(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None, style_id: UUID | None = None, status: str | None = None,
    ) -> list[dict]:
        from app.services.production import ProductionService, compute_lot_cost_summary

        svc = ProductionService(self.db)
        lots, _ = await svc.list_lots(company_id, status=status, page=1, page_size=1000)

        customer_ids = {lot.customer_id for lot in lots if lot.customer_id}
        customer_names: dict[UUID, str] = {}
        if customer_ids:
            res = await self.db.execute(select(Customer.id, Customer.legal_name).where(Customer.id.in_(customer_ids)))
            customer_names = {r[0]: r[1] for r in res}

        rows = []
        for lot in lots:
            lot_date = lot.created_at.date() if lot.created_at else None
            if lot_date and not (from_date <= lot_date <= to_date):
                continue
            if customer_id and lot.customer_id != customer_id:
                continue
            if style_id and lot.style_id != style_id:
                continue
            selling_prices = await svc.resolve_selling_prices(lot)
            s = compute_lot_cost_summary(lot, selling_prices)
            rows.append({
                "lot_number": lot.lot_number,
                "style_name": lot.style.name if lot.style else "—",
                "customer_name": customer_names.get(lot.customer_id, "—") if lot.customer_id else "—",
                "status": lot.status,
                "lot_date": lot_date,
                "planned_qty": lot.planned_qty,
                "first_quality_qty": s.first_quality_qty,
                "rejected_qty": s.rejected_qty,
                "yield_pct": s.yield_pct,
                "cost_per_piece": s.cost_per_first_quality_piece,
                "selling_price_per_piece": s.actual_selling_price_per_piece,
                "profit_per_piece": s.profit_per_piece,
                "margin_pct": s.gross_margin_pct,
                "total_actual_cost": s.total_actual,
                "total_profit": s.actual_profit,
                "is_final": s.is_final,
            })
        rows.sort(key=lambda r: r["lot_date"] or date.min, reverse=True)
        return rows

    # ── Job-Work Outstanding (open vendor/worker challans) ──────────────────

    async def job_work_outstanding(
        self, company_id: UUID, vendor_id: UUID | None = None,
        worker_id: UUID | None = None, stage_type: str | None = None,
    ) -> list[dict]:
        clauses = [
            "pl.company_id = :cid",
            "c.status != 'received'",
            "(c.out_qty - COALESCE(c.in_qty, 0) - COALESCE(c.rejected_qty, 0)) > 0",
        ]
        params: dict = {"cid": str(company_id)}
        if vendor_id:
            clauses.append("c.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        if worker_id:
            clauses.append("c.worker_id = :wkid")
            params["wkid"] = str(worker_id)
        if stage_type:
            clauses.append("ps.stage_type = :stype")
            params["stype"] = stage_type
        result = await self.db.execute(
            text(f"""
                SELECT
                    c.challan_number,
                    COALESCE(v.name, w.name, '—') AS assignee_name,
                    CASE WHEN c.vendor_id IS NOT NULL THEN 'vendor' ELSE 'internal_worker' END AS assignee_type,
                    pl.lot_number, ps.stage_name, ps.stage_type,
                    c.out_date, c.out_qty, c.in_date, COALESCE(c.in_qty, 0) AS in_qty,
                    COALESCE(c.rejected_qty, 0) AS rejected_qty,
                    (c.out_qty - COALESCE(c.in_qty, 0) - COALESCE(c.rejected_qty, 0)) AS pending_qty,
                    (CURRENT_DATE - c.out_date) AS age_days,
                    c.status, c.bill_amount, c.bill_received
                FROM production_stage_challans c
                JOIN production_stages ps ON ps.id = c.production_stage_id
                JOIN production_lots pl ON pl.id = ps.production_lot_id
                LEFT JOIN vendors v ON v.id = c.vendor_id
                LEFT JOIN internal_workers w ON w.id = c.worker_id
                WHERE {" AND ".join(clauses)}
                ORDER BY c.out_date ASC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Material Consumption ─────────────────────────────────────────────────

    async def material_consumption(
        self, company_id: UUID, from_date: date, to_date: date,
        lot_id: UUID | None = None, product_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["mi.company_id = :cid", "mi.issue_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if lot_id:
            clauses.append("mi.production_lot_id = :lid")
            params["lid"] = str(lot_id)
        if product_id:
            clauses.append("mii.product_id = :pid")
            params["pid"] = str(product_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    pl.lot_number, p.name AS product_name, mi.issue_number, mi.issue_date,
                    mii.issued_qty, u.abbreviation AS unit_symbol, mii.unit_cost, mii.total_cost,
                    COALESCE(ps.stage_name, '—') AS stage_name
                FROM material_issue_items mii
                JOIN material_issues mi ON mi.id = mii.material_issue_id
                JOIN production_lots pl ON pl.id = mi.production_lot_id
                JOIN products p ON p.id = mii.product_id
                JOIN units u ON u.id = mii.unit_id
                LEFT JOIN production_stages ps ON ps.id = mi.stage_id
                WHERE {" AND ".join(clauses)}
                ORDER BY mi.issue_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Receipt Register (customer payments) ─────────────────────────────────

    async def receipt_register(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None, payment_mode: str | None = None,
    ) -> list[dict]:
        clauses = ["p.company_id = :cid", "p.payment_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if customer_id:
            clauses.append("p.customer_id = :cust")
            params["cust"] = str(customer_id)
        if payment_mode:
            clauses.append("p.payment_mode = :mode")
            params["mode"] = payment_mode
        result = await self.db.execute(
            text(f"""
                SELECT
                    p.payment_number, c.legal_name AS customer_name, p.payment_date,
                    p.amount, p.payment_mode, p.reference, p.status
                FROM payments p
                JOIN customers c ON c.id = p.customer_id
                WHERE {" AND ".join(clauses)}
                ORDER BY p.payment_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Payment Register (vendor payments) ───────────────────────────────────

    async def payment_register(
        self, company_id: UUID, from_date: date, to_date: date,
        vendor_id: UUID | None = None, payment_mode: str | None = None,
    ) -> list[dict]:
        clauses = ["p.company_id = :cid", "p.payment_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if vendor_id:
            clauses.append("p.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        if payment_mode:
            clauses.append("p.payment_mode = :mode")
            params["mode"] = payment_mode
        result = await self.db.execute(
            text(f"""
                SELECT
                    p.payment_number, v.name AS vendor_name, p.payment_date,
                    p.amount, p.payment_mode, p.reference, p.status
                FROM vendor_payments p
                JOIN vendors v ON v.id = p.vendor_id
                WHERE {" AND ".join(clauses)}
                ORDER BY p.payment_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Credit Note Register ─────────────────────────────────────────────────

    async def credit_note_register(
        self, company_id: UUID, from_date: date, to_date: date,
        customer_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["cn.company_id = :cid", "cn.credit_note_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if customer_id:
            clauses.append("cn.customer_id = :cust")
            params["cust"] = str(customer_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    cn.credit_note_number, c.legal_name AS customer_name, cn.credit_note_date,
                    cn.total_amount, cn.status, cn.reason, i.invoice_number
                FROM credit_notes cn
                JOIN customers c ON c.id = cn.customer_id
                LEFT JOIN invoices i ON i.id = cn.invoice_id
                WHERE {" AND ".join(clauses)}
                ORDER BY cn.credit_note_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── Debit Note Register ──────────────────────────────────────────────────

    async def debit_note_register(
        self, company_id: UUID, from_date: date, to_date: date,
        vendor_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["dn.company_id = :cid", "dn.debit_note_date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if vendor_id:
            clauses.append("dn.vendor_id = :vid")
            params["vid"] = str(vendor_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    dn.debit_note_number, v.name AS vendor_name, dn.debit_note_date,
                    dn.total_amount, dn.status, dn.reason, pe.entry_number
                FROM debit_notes dn
                JOIN vendors v ON v.id = dn.vendor_id
                LEFT JOIN purchase_entries pe ON pe.id = dn.purchase_entry_id
                WHERE {" AND ".join(clauses)}
                ORDER BY dn.debit_note_date DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── CRM: Lead Conversion & Ageing ─────────────────────────────────────────

    async def lead_conversion_ageing(
        self, company_id: UUID, from_date: date, to_date: date,
        pipeline_id: UUID | None = None, source_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["cl.company_id = :cid", "cl.created_at::date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if pipeline_id:
            clauses.append("cl.pipeline_id = :pid")
            params["pid"] = str(pipeline_id)
        if source_id:
            clauses.append("cl.source_id = :sid")
            params["sid"] = str(source_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    cl.title, COALESCE(cps.name, '—') AS stage_name,
                    COALESCE(cls.name, '—') AS source_name, cl.lead_value, cl.status, cl.temperature,
                    cl.created_at::date AS created_date, cl.closed_at::date AS closed_date,
                    (CURRENT_DATE - COALESCE(
                        (SELECT MAX(h.changed_at) FROM crm_lead_stage_history h WHERE h.lead_id = cl.id)::date,
                        cl.created_at::date
                    )) AS days_in_stage
                FROM crm_leads cl
                LEFT JOIN crm_pipeline_stages cps ON cps.id = cl.stage_id
                LEFT JOIN crm_lead_sources cls ON cls.id = cl.source_id
                WHERE {" AND ".join(clauses)}
                ORDER BY cl.created_at DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── CRM: Employee Task Performance ───────────────────────────────────────

    async def employee_task_performance(self, company_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT
                    u.full_name AS employee_name,
                    COUNT(*) FILTER (WHERE t.status = 'pending')                                   AS pending,
                    COUNT(*) FILTER (WHERE t.status = 'in_progress')                                AS in_progress,
                    COUNT(*) FILTER (WHERE t.status IN ('pending','in_progress') AND t.due_at < NOW()) AS overdue,
                    COUNT(*) FILTER (
                        WHERE t.status = 'completed' AND t.completed_at >= DATE_TRUNC('week', NOW())
                    ) AS completed_this_week
                FROM crm_tasks t
                JOIN users u ON u.id = t.assigned_to
                WHERE t.company_id = :cid
                GROUP BY u.id, u.full_name
                ORDER BY overdue DESC, pending DESC
            """),
            {"cid": str(company_id)},
        )
        return [dict(r._mapping) for r in result]

    # ── CRM: Platform-Wise Lead Analytics ────────────────────────────────────

    async def platform_lead_analytics(
        self, company_id: UUID, from_date: date, to_date: date,
        source_id: UUID | None = None, assigned_to: UUID | None = None,
        status: str | None = None, customer_id: UUID | None = None,
    ) -> list[dict]:
        clauses = ["cl.company_id = :cid", "cl.created_at::date BETWEEN :fd AND :td"]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if source_id:
            clauses.append("cl.source_id = :sid")
            params["sid"] = str(source_id)
        if assigned_to:
            clauses.append("cl.assigned_to = :aid")
            params["aid"] = str(assigned_to)
        if status:
            clauses.append("cl.status = :status")
            params["status"] = status
        if customer_id:
            clauses.append("cl.customer_id = :custid")
            params["custid"] = str(customer_id)
        result = await self.db.execute(
            text(f"""
                SELECT
                    COALESCE(cls.name, 'Unassigned') AS source_name,
                    COUNT(*) AS total_leads,
                    COUNT(*) FILTER (WHERE cl.temperature IN ('warm', 'hot')) AS qualified_leads,
                    COUNT(*) FILTER (WHERE cl.status = 'won') AS converted_leads,
                    COUNT(*) FILTER (WHERE cl.status = 'lost') AS lost_leads,
                    ROUND(
                        COUNT(*) FILTER (WHERE cl.status = 'won')::numeric
                        / NULLIF(COUNT(*), 0) * 100, 1
                    ) AS conversion_rate,
                    COALESCE(SUM(cl.lead_value) FILTER (WHERE cl.status = 'won'), 0) AS revenue_generated,
                    ROUND(COALESCE(AVG(cl.lead_value), 0), 2) AS avg_lead_value
                FROM crm_leads cl
                LEFT JOIN crm_lead_sources cls ON cls.id = cl.source_id
                WHERE {" AND ".join(clauses)}
                GROUP BY cls.name
                ORDER BY total_leads DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]

    # ── CRM: Lead Acquisition Cost ───────────────────────────────────────────
    # Platform-level only — a lead can't be attributed to a specific campaign
    # (no campaign field on CrmLead), so campaign-level cost-per-lead would
    # divide a real spend by a lead count that isn't actually attributable to
    # it. Every ratio is NULL (not 0) when its denominator or spend is 0.

    async def lead_acquisition_cost(
        self, company_id: UUID, from_date: date, to_date: date,
        source_id: UUID | None = None,
    ) -> list[dict]:
        lead_clauses = ["cl.company_id = :cid", "cl.created_at::date BETWEEN :fd AND :td"]
        spend_clauses = [
            "sp.company_id = :cid",
            "sp.period_start <= :td", "sp.period_end >= :fd",
        ]
        params: dict = {"cid": str(company_id), "fd": from_date, "td": to_date}
        if source_id:
            lead_clauses.append("cl.source_id = :sid")
            spend_clauses.append("sp.source_id = :sid")
            params["sid"] = str(source_id)

        result = await self.db.execute(
            text(f"""
                WITH lead_stats AS (
                    SELECT
                        cl.source_id,
                        COUNT(*) AS total_leads,
                        COUNT(*) FILTER (WHERE cl.temperature IN ('warm', 'hot')) AS qualified_leads,
                        COUNT(*) FILTER (WHERE cl.status = 'won') AS converted_leads,
                        COALESCE(SUM(cl.lead_value) FILTER (WHERE cl.status = 'won'), 0) AS revenue_generated
                    FROM crm_leads cl
                    WHERE {" AND ".join(lead_clauses)}
                    GROUP BY cl.source_id
                ),
                spend_stats AS (
                    SELECT sp.source_id, SUM(sp.amount) AS total_ad_spend
                    FROM crm_ad_spend sp
                    WHERE {" AND ".join(spend_clauses)}
                    GROUP BY sp.source_id
                )
                SELECT
                    COALESCE(cls.name, 'Unassigned') AS source_name,
                    COALESCE(ls.total_leads, 0) AS total_leads,
                    COALESCE(ls.qualified_leads, 0) AS qualified_leads,
                    COALESCE(ls.converted_leads, 0) AS converted_leads,
                    COALESCE(ls.revenue_generated, 0) AS revenue_generated,
                    COALESCE(ss.total_ad_spend, 0) AS total_ad_spend,
                    CASE WHEN COALESCE(ss.total_ad_spend, 0) > 0 AND COALESCE(ls.total_leads, 0) > 0
                        THEN ROUND(ss.total_ad_spend / ls.total_leads, 2) END AS cost_per_lead,
                    CASE WHEN COALESCE(ss.total_ad_spend, 0) > 0 AND COALESCE(ls.qualified_leads, 0) > 0
                        THEN ROUND(ss.total_ad_spend / ls.qualified_leads, 2) END AS cost_per_qualified_lead,
                    CASE WHEN COALESCE(ss.total_ad_spend, 0) > 0 AND COALESCE(ls.converted_leads, 0) > 0
                        THEN ROUND(ss.total_ad_spend / ls.converted_leads, 2) END AS cost_per_conversion,
                    CASE WHEN COALESCE(ss.total_ad_spend, 0) > 0
                        THEN ROUND(COALESCE(ls.revenue_generated, 0) / ss.total_ad_spend, 2) END AS roas
                FROM lead_stats ls
                FULL OUTER JOIN spend_stats ss ON ss.source_id = ls.source_id
                LEFT JOIN crm_lead_sources cls ON cls.id = COALESCE(ls.source_id, ss.source_id)
                ORDER BY total_ad_spend DESC, total_leads DESC
            """),
            params,
        )
        return [dict(r._mapping) for r in result]
