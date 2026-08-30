"""ReportsService: aggregated read-only queries for all report pages."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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

    async def stock_ageing(self, company_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text("""
                WITH stock_balance AS (
                    SELECT
                        it.product_id,
                        it.warehouse_id,
                        it.unit_id,
                        SUM(it.quantity * it.direction) AS balance
                    FROM inventory_transactions it
                    WHERE it.company_id = :cid
                    GROUP BY it.product_id, it.warehouse_id, it.unit_id
                    HAVING SUM(it.quantity * it.direction) > 0
                ),
                earliest_receipt AS (
                    SELECT
                        product_id,
                        warehouse_id,
                        MIN(transaction_date) AS first_date
                    FROM inventory_transactions
                    WHERE company_id = :cid AND direction = 1
                    GROUP BY product_id, warehouse_id
                )
                SELECT
                    p.name              AS product_name,
                    p.product_type,
                    w.name              AS warehouse_name,
                    u.symbol            AS unit_symbol,
                    sb.balance,
                    er.first_date       AS oldest_receipt_date,
                    (CURRENT_DATE - er.first_date) AS age_days,
                    CASE
                        WHEN (CURRENT_DATE - er.first_date) <= 30  THEN '0-30 days'
                        WHEN (CURRENT_DATE - er.first_date) <= 60  THEN '31-60 days'
                        WHEN (CURRENT_DATE - er.first_date) <= 90  THEN '61-90 days'
                        ELSE '90+ days'
                    END                 AS age_bucket
                FROM stock_balance sb
                JOIN products   p ON p.id = sb.product_id
                JOIN warehouses w ON w.id = sb.warehouse_id
                JOIN units      u ON u.id = sb.unit_id
                LEFT JOIN earliest_receipt er
                    ON er.product_id   = sb.product_id
                    AND er.warehouse_id = sb.warehouse_id
                ORDER BY age_days DESC NULLS LAST
            """),
            {"cid": str(company_id)},
        )
        return [dict(r._mapping) for r in result]
