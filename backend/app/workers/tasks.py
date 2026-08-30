import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from app.workers.celery_app import celery_app


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.refresh_inventory_balance")
def refresh_inventory_balance():
    from app.db.session import AsyncSessionLocal

    async def _refresh():
        async with AsyncSessionLocal() as db:
            conn = await db.connection()
            await conn.execute(text("COMMIT"))
            try:
                await conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY inventory_balance"))
            except Exception:
                pass  # view may not exist in all environments

    _run(_refresh())


@celery_app.task(name="app.workers.tasks.expire_refresh_tokens")
def expire_refresh_tokens():
    from app.db.session import AsyncSessionLocal

    async def _expire():
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM refresh_tokens WHERE expires_at < :now"),
                {"now": datetime.now(timezone.utc)},
            )
            await db.commit()

    _run(_expire())


@celery_app.task(name="app.workers.tasks.check_low_stock")
def check_low_stock():
    """Find products with zero or negative stock and create notifications."""
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification

    async def _check():
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT
                    t.company_id,
                    p.name AS product_name,
                    p.product_type,
                    w.name AS warehouse_name,
                    SUM(t.quantity * t.direction) AS balance
                FROM inventory_transactions t
                JOIN products  p ON p.id = t.product_id
                JOIN warehouses w ON w.id = t.warehouse_id
                GROUP BY t.company_id, p.name, p.product_type, w.name
                HAVING SUM(t.quantity * t.direction) <= 0
            """))
            rows = result.mappings().all()
            for row in rows:
                company_id = row["company_id"]
                notif = await create_notification(
                    db,
                    company_id=company_id,
                    notification_type="low_stock",
                    title=f"Out of Stock: {row['product_name']}",
                    body=f"{row['product_name']} ({row['product_type']}) has zero stock in {row['warehouse_name']}.",
                    data={"product_name": row["product_name"], "warehouse": row["warehouse_name"]},
                )
                await db.commit()
                publish_notification(str(company_id), {
                    "type": "low_stock",
                    "title": notif.title,
                    "body": notif.body,
                    "id": str(notif.id),
                })

    _run(_check())


@celery_app.task(name="app.workers.tasks.check_overdue_payments")
def check_overdue_payments():
    """Find invoices past due date and create notifications."""
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification

    async def _check():
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT
                    inv.company_id,
                    c.name AS customer_name,
                    inv.invoice_number,
                    inv.due_date,
                    inv.balance_amount
                FROM invoices inv
                JOIN customers c ON c.id = inv.customer_id
                WHERE inv.due_date < CURRENT_DATE
                  AND inv.balance_amount > 0
                  AND inv.payment_status IN ('unpaid', 'partial', 'overdue')
                ORDER BY inv.due_date ASC
            """))
            rows = result.mappings().all()
            if not rows:
                return

            # Group by company and create one summary notification per company
            from collections import defaultdict
            by_company: dict = defaultdict(list)
            for r in rows:
                by_company[r["company_id"]].append(r)

            for company_id, invoices in by_company.items():
                total_overdue = sum(float(inv["balance_amount"]) for inv in invoices)
                body = (
                    f"{len(invoices)} invoice(s) are overdue. "
                    f"Total outstanding: ₹{total_overdue:,.2f}. "
                    f"Oldest: {invoices[0]['customer_name']} — {invoices[0]['invoice_number']}."
                )
                notif = await create_notification(
                    db,
                    company_id=company_id,
                    notification_type="overdue_payment",
                    title=f"{len(invoices)} Overdue Invoice(s)",
                    body=body,
                    data={"count": len(invoices), "total": total_overdue},
                )
                await db.commit()
                publish_notification(str(company_id), {
                    "type": "overdue_payment",
                    "title": notif.title,
                    "body": notif.body,
                    "id": str(notif.id),
                })

    _run(_check())


@celery_app.task(name="app.workers.tasks.check_production_delays")
def check_production_delays():
    """Find production lots past delivery date that are not completed."""
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification

    async def _check():
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT
                    pl.company_id,
                    pl.lot_number,
                    s.style_name,
                    pl.delivery_date,
                    pl.status
                FROM production_lots pl
                LEFT JOIN styles s ON s.id = pl.style_id
                WHERE pl.delivery_date < CURRENT_DATE
                  AND pl.status NOT IN ('completed', 'cancelled')
                ORDER BY pl.delivery_date ASC
            """))
            rows = result.mappings().all()
            if not rows:
                return

            from collections import defaultdict
            by_company: dict = defaultdict(list)
            for r in rows:
                by_company[r["company_id"]].append(r)

            for company_id, lots in by_company.items():
                body = (
                    f"{len(lots)} production lot(s) are past their delivery date. "
                    f"Most delayed: {lots[0]['lot_number']} "
                    f"({lots[0]['style_name'] or 'N/A'}) — due {lots[0]['delivery_date']}."
                )
                notif = await create_notification(
                    db,
                    company_id=company_id,
                    notification_type="production_delay",
                    title=f"{len(lots)} Production Lot(s) Delayed",
                    body=body,
                    data={"count": len(lots)},
                )
                await db.commit()
                publish_notification(str(company_id), {
                    "type": "production_delay",
                    "title": notif.title,
                    "body": notif.body,
                    "id": str(notif.id),
                })

    _run(_check())


@celery_app.task(name="app.workers.tasks.generate_report")
def generate_report(report_type: str, params: dict, user_id: str):
    pass
