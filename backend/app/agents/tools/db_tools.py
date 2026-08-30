"""Database-backed query functions for ERP agent tools."""
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def query_stock_balance(
    db: AsyncSession, company_id: str, product_name: str | None = None
) -> list[dict]:
    sql = """
    SELECT
        p.name               AS product_name,
        p.product_type,
        w.name               AS warehouse_name,
        u.abbreviation       AS unit,
        SUM(t.quantity * t.direction) AS quantity
    FROM inventory_transactions t
    JOIN products  p ON p.id = t.product_id
    JOIN warehouses w ON w.id = t.warehouse_id
    JOIN units      u ON u.id = t.unit_id
    WHERE t.company_id = :cid
    {filter}
    GROUP BY p.name, p.product_type, w.name, u.abbreviation
    HAVING SUM(t.quantity * t.direction) > 0
    ORDER BY p.name, w.name
    """
    params: dict = {"cid": company_id}
    if product_name:
        sql = sql.replace("{filter}", "AND LOWER(p.name) LIKE :pname")
        params["pname"] = f"%{product_name.lower()}%"
    else:
        sql = sql.replace("{filter}", "")
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_recent_transactions(
    db: AsyncSession, company_id: str,
    product_name: str | None = None, limit: int = 10
) -> list[dict]:
    sql = """
    SELECT
        t.transaction_date::text,
        t.transaction_type,
        CASE WHEN t.direction = 1 THEN 'IN' ELSE 'OUT' END AS direction,
        t.quantity::float,
        p.name AS product_name,
        w.name AS warehouse_name,
        u.abbreviation AS unit,
        t.reference_number
    FROM inventory_transactions t
    JOIN products  p ON p.id = t.product_id
    JOIN warehouses w ON w.id = t.warehouse_id
    JOIN units      u ON u.id = t.unit_id
    WHERE t.company_id = :cid
    {filter}
    ORDER BY t.transaction_date DESC
    LIMIT :limit
    """
    params: dict = {"cid": company_id, "limit": limit}
    if product_name:
        sql = sql.replace("{filter}", "AND LOWER(p.name) LIKE :pname")
        params["pname"] = f"%{product_name.lower()}%"
    else:
        sql = sql.replace("{filter}", "")
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_sales_orders(
    db: AsyncSession, company_id: str,
    status: str | None = None, customer_name: str | None = None, limit: int = 10
) -> list[dict]:
    filters = []
    params: dict = {"cid": company_id, "limit": limit}
    if status:
        filters.append("so.status = :status")
        params["status"] = status
    if customer_name:
        filters.append("LOWER(c.name) LIKE :cname")
        params["cname"] = f"%{customer_name.lower()}%"
    where_extra = ("AND " + " AND ".join(filters)) if filters else ""
    sql = f"""
    SELECT
        so.order_number,
        so.order_date::text,
        so.status,
        so.delivery_date::text,
        c.name AS customer_name,
        so.total_amount::float
    FROM sales_orders so
    JOIN customers c ON c.id = so.customer_id
    WHERE so.company_id = :cid {where_extra}
    ORDER BY so.order_date DESC
    LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_outstanding_invoices(
    db: AsyncSession, company_id: str, customer_name: str | None = None
) -> list[dict]:
    params: dict = {"cid": company_id}
    extra = ""
    if customer_name:
        extra = "AND LOWER(c.legal_name) LIKE :cname"
        params["cname"] = f"%{customer_name.lower()}%"
    sql = f"""
    SELECT
        inv.invoice_number,
        inv.invoice_date::text,
        inv.due_date::text,
        c.legal_name AS customer_name,
        inv.total_amount::float,
        inv.status
    FROM invoices inv
    JOIN customers c ON c.id = inv.customer_id
    WHERE inv.company_id = :cid
      AND inv.status IN ('unpaid', 'partial', 'overdue')
      {extra}
    ORDER BY inv.due_date ASC
    """
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_revenue_summary(
    db: AsyncSession, company_id: str, period: str | None = None
) -> list[dict]:
    """Total invoiced revenue, optionally grouped by month or customer."""
    period_filter = ""
    params: dict = {"cid": company_id}
    if period == "month":
        sql = """
        SELECT
            TO_CHAR(inv.invoice_date, 'YYYY-MM') AS month,
            COUNT(*)                              AS invoice_count,
            SUM(inv.total_amount)::float          AS total_revenue,
            SUM(inv.taxable_amount)::float        AS taxable_amount,
            SUM(inv.cgst_amount + inv.sgst_amount + inv.igst_amount)::float AS total_tax
        FROM invoices inv
        WHERE inv.company_id = :cid
        GROUP BY TO_CHAR(inv.invoice_date, 'YYYY-MM')
        ORDER BY month DESC
        LIMIT 12
        """
    elif period == "customer":
        sql = """
        SELECT
            c.legal_name              AS customer_name,
            COUNT(inv.id)             AS invoice_count,
            SUM(inv.total_amount)::float AS total_revenue
        FROM invoices inv
        JOIN customers c ON c.id = inv.customer_id
        WHERE inv.company_id = :cid
        GROUP BY c.legal_name
        ORDER BY total_revenue DESC
        LIMIT 20
        """
    else:
        sql = """
        SELECT
            COUNT(*)                              AS total_invoices,
            SUM(inv.total_amount)::float          AS total_revenue,
            SUM(inv.taxable_amount)::float        AS taxable_amount,
            SUM(inv.cgst_amount + inv.sgst_amount + inv.igst_amount)::float AS total_tax,
            MIN(inv.invoice_date)::text           AS from_date,
            MAX(inv.invoice_date)::text           AS to_date
        FROM invoices inv
        WHERE inv.company_id = :cid
        """
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_production_lots(
    db: AsyncSession, company_id: str,
    status: str | None = None, limit: int = 10
) -> list[dict]:
    params: dict = {"cid": company_id, "limit": limit}
    extra = ""
    if status:
        extra = "AND pl.status = :status"
        params["status"] = status
    sql = f"""
    SELECT
        pl.lot_number,
        pl.lot_date::text,
        pl.status,
        pl.planned_qty,
        pl.actual_qty,
        pl.delivery_date::text,
        s.style_code,
        s.style_name
    FROM production_lots pl
    LEFT JOIN styles s ON s.id = pl.style_id
    WHERE pl.company_id = :cid {extra}
    ORDER BY pl.lot_date DESC
    LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


async def query_vendor_outstanding(db: AsyncSession, company_id: str) -> list[dict]:
    sql = """
    SELECT
        v.name AS vendor_name,
        v.vendor_type,
        SUM(pe.total_amount)::float   AS total_purchases,
        SUM(pe.paid_amount)::float    AS total_paid,
        SUM(pe.balance_amount)::float AS outstanding
    FROM purchase_entries pe
    JOIN vendors v ON v.id = pe.vendor_id
    WHERE pe.company_id = :cid
      AND pe.payment_status IN ('unpaid', 'partial')
    GROUP BY v.name, v.vendor_type
    HAVING SUM(pe.balance_amount) > 0
    ORDER BY outstanding DESC
    """
    result = await db.execute(text(sql), {"cid": company_id})
    return [dict(r) for r in result.mappings().all()]


async def query_purchase_orders(
    db: AsyncSession, company_id: str,
    status: str | None = None, limit: int = 10
) -> list[dict]:
    params: dict = {"cid": company_id, "limit": limit}
    extra = ""
    if status:
        extra = "AND po.status = :status"
        params["status"] = status
    sql = f"""
    SELECT
        po.po_number,
        po.po_date::text,
        po.status,
        po.expected_delivery::text,
        v.name AS vendor_name,
        po.total_amount::float
    FROM purchase_orders po
    JOIN vendors v ON v.id = po.vendor_id
    WHERE po.company_id = :cid {extra}
    ORDER BY po.po_date DESC
    LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


def to_json(data: object) -> str:
    return json.dumps(data, default=str)
