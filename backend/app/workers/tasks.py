import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from app.workers.celery_app import celery_app


def _run(coro):
    """Run an async coroutine from a sync Celery task.

    Disposes the shared async engine's connection pool on this loop before
    closing it - otherwise a connection checked into the pool under this
    loop gets handed to the next task's brand-new event loop and asyncpg
    raises "attached to a different loop" (pre-existing bug, surfaced by
    this worker process running many tasks over its lifetime; fixed here
    since every task funnels through this helper)."""
    from app.db.session import engine

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(engine.dispose())
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


@celery_app.task(name="app.workers.tasks.check_job_work_challans")
def check_job_work_challans():
    """Find job-work challans that haven't returned within their expected window,
    and received challans whose vendor bill still hasn't come in — see
    Garments_ERP_Style_Master_Specification.md §47.11 / §47.12.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification
    from collections import defaultdict

    async def _check():
        async with AsyncSessionLocal() as db:
            overdue = (await db.execute(text("""
                SELECT
                    pl.company_id,
                    pc.challan_number,
                    pc.out_date,
                    pc.expected_return_days,
                    v.name AS vendor_name,
                    ps.stage_name,
                    pl.lot_number
                FROM production_stage_challans pc
                JOIN production_stages ps ON ps.id = pc.production_stage_id
                JOIN production_lots pl ON pl.id = ps.production_lot_id
                JOIN vendors v ON v.id = pc.vendor_id
                WHERE pc.status = 'out'
                  AND pc.expected_return_days IS NOT NULL
                  AND pc.out_date + (pc.expected_return_days || ' days')::interval < NOW()
                ORDER BY pc.out_date ASC
            """))).mappings().all()

            by_company: dict = defaultdict(list)
            for r in overdue:
                by_company[r["company_id"]].append(r)
            for company_id, challans in by_company.items():
                first = challans[0]
                body = (
                    f"{len(challans)} job-work challan(s) haven't returned from the vendor within "
                    f"the expected window. Oldest: {first['challan_number']} — {first['stage_name']} "
                    f"on {first['lot_number']}, sent to {first['vendor_name']} on {first['out_date']}."
                )
                notif = await create_notification(
                    db, company_id=company_id, notification_type="job_work_overdue",
                    title=f"{len(challans)} Job-Work Challan(s) Overdue",
                    body=body, data={"count": len(challans)},
                )
                await db.commit()
                publish_notification(str(company_id), {
                    "type": "job_work_overdue", "title": notif.title, "body": notif.body, "id": str(notif.id),
                })

            bill_pending = (await db.execute(text("""
                SELECT
                    pl.company_id,
                    pc.challan_number,
                    pc.status,
                    COALESCE(pc.in_date, pc.out_date) AS reference_date,
                    v.name AS vendor_name,
                    ps.stage_name,
                    pl.lot_number
                FROM production_stage_challans pc
                JOIN production_stages ps ON ps.id = pc.production_stage_id
                JOIN production_lots pl ON pl.id = ps.production_lot_id
                JOIN companies co ON co.id = pl.company_id
                JOIN vendors v ON v.id = pc.vendor_id
                WHERE pc.status <> 'cancelled'
                  AND pc.bill_received = false
                  AND COALESCE(pc.in_date, pc.out_date)
                      < CURRENT_DATE - make_interval(days => co.bill_alert_days)
                ORDER BY reference_date ASC
            """))).mappings().all()

            by_company = defaultdict(list)
            for r in bill_pending:
                by_company[r["company_id"]].append(r)
            for company_id, challans in by_company.items():
                first = challans[0]
                body = (
                    f"{len(challans)} job-work challan(s) are past the bill alert window with the vendor's bill "
                    f"still pending. Oldest: {first['challan_number']} — {first['stage_name']} "
                    f"on {first['lot_number']}, from {first['vendor_name']}, dated {first['reference_date']}."
                )
                notif = await create_notification(
                    db, company_id=company_id, notification_type="job_work_bill_pending",
                    title=f"{len(challans)} Job-Work Bill(s) Pending",
                    body=body, data={"count": len(challans)},
                )
                await db.commit()
                publish_notification(str(company_id), {
                    "type": "job_work_bill_pending", "title": notif.title, "body": notif.body, "id": str(notif.id),
                })

    _run(_check())


@celery_app.task(name="app.workers.tasks.generate_report")
def generate_report(report_type: str, params: dict, user_id: str):
    pass


@celery_app.task(name="app.workers.tasks.mark_rotten_leads")
def mark_rotten_leads():
    """Flag leads that have sat in a non-terminal stage past pipeline.rotten_days."""
    import logging
    from app.db.session import AsyncSessionLocal

    log = logging.getLogger(__name__)

    async def _mark():
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                UPDATE crm_leads l
                SET rotten_at = NOW()
                FROM crm_pipelines p
                WHERE l.pipeline_id = p.id
                  AND l.status = 'open'
                  AND l.rotten_at IS NULL
                  AND p.rotten_days IS NOT NULL
                  AND l.updated_at < NOW() - (p.rotten_days || ' days')::INTERVAL
                RETURNING l.id
            """))
            rows = result.fetchall()
            await db.commit()
            count = len(rows)
            if count:
                log.info("mark_rotten_leads: flagged %d lead(s) as rotten", count)
            else:
                log.debug("mark_rotten_leads: no rotten leads found")

    _run(_mark())


@celery_app.task(name="app.workers.tasks.flag_missed_followups")
def flag_missed_followups():
    """Find leads whose scheduled follow-up has passed and create a task +
    notification for the assignee. Does not touch crm_leads.follow_up_status
    — that field's only writer is _sync_lead_followup_fields in the API
    layer (recomputed from the activity timeline); this job only observes
    the same overdue condition the dashboard/list filter already compute.
    Idempotent: skips leads that already have an open missed-follow-up task.
    """
    import logging
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification

    log = logging.getLogger(__name__)

    async def _flag():
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT l.id AS lead_id, l.company_id, l.title, l.assigned_to
                FROM crm_leads l
                WHERE l.follow_up_status = 'scheduled'
                  AND l.next_follow_up_at < NOW()
                  AND l.assigned_to IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM crm_tasks t
                      WHERE t.lead_id = l.id
                        AND t.source = 'missed_follow_up'
                        AND t.status IN ('pending', 'in_progress')
                  )
            """))
            rows = result.mappings().all()
            now = datetime.now(timezone.utc)
            for row in rows:
                await db.execute(text("""
                    INSERT INTO crm_tasks
                        (id, company_id, title, lead_id, assigned_to, due_at, priority, status, source, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :cid, :title, :lead_id, :assignee, :due_at, 'high', 'pending', 'missed_follow_up', :now, :now)
                """), {
                    "cid": row["company_id"], "title": f"Missed follow-up: {row['title']}",
                    "lead_id": row["lead_id"], "assignee": row["assigned_to"], "due_at": now, "now": now,
                })
                notif = await create_notification(
                    db, company_id=row["company_id"], notification_type="missed_follow_up",
                    title="Missed follow-up",
                    body=f"The follow-up for \"{row['title']}\" is overdue.",
                    user_id=row["assigned_to"], data={"lead_id": str(row["lead_id"])},
                )
                await db.commit()
                try:
                    publish_notification(str(row["company_id"]), {
                        "type": "missed_follow_up", "title": notif.title, "body": notif.body,
                        "id": str(notif.id), "user_id": str(row["assigned_to"]),
                    })
                except Exception:
                    log.warning("Failed to publish missed_follow_up notification", exc_info=True)

            if rows:
                log.info("flag_missed_followups: created %d task(s)", len(rows))

            from app.models.crm import CrmLead
            from app.models.user import User as _User
            from app.services.whatsapp_automation import fire_event, resolve_customer_name

            for row in rows:
                lead_obj = await db.get(CrmLead, row["lead_id"])
                if not lead_obj:
                    continue
                assignee = await db.get(_User, lead_obj.assigned_to) if lead_obj.assigned_to else None
                context = {
                    "customer_name": await resolve_customer_name(db, lead_obj),
                    "followup_date": lead_obj.next_follow_up_at.strftime("%d %b %Y") if lead_obj.next_follow_up_at else "",
                    "employee_name": assignee.full_name or "" if assignee else "",
                }
                await fire_event(db, row["company_id"], "follow_up_due", context, lead=lead_obj)
            await db.commit()

    _run(_flag())


@celery_app.task(name="app.workers.tasks.escalate_uncontacted_high_priority_leads")
def escalate_uncontacted_high_priority_leads():
    """Phase 2 Step 8: a HIGH-priority lead that nobody has made first
    contact with yet gets escalated in two stages — first a reminder to
    the assigned employee (after companies.escalation_employee_hours past
    its response_target_at), then a notification to the company owner(s)
    (after escalation_manager_hours). Each stage notifies at most once per
    lead (gated by escalation_employee_notified_at /
    escalation_manager_notified_at) — idempotency, spec Step 18. Distinct
    from flag_missed_followups: this is about a lead nobody has touched at
    all yet, not an already-scheduled follow-up that lapsed."""
    import logging
    from app.db.session import AsyncSessionLocal
    from app.services.notification import create_notification, publish_notification

    log = logging.getLogger(__name__)

    async def _escalate():
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)

            employee_due = await db.execute(text("""
                SELECT l.id, l.company_id, l.title, l.assigned_to, c.escalation_employee_hours
                FROM crm_leads l JOIN companies c ON c.id = l.company_id
                WHERE l.priority = 'high'
                  AND l.first_contacted_at IS NULL
                  AND l.response_target_at IS NOT NULL
                  AND l.escalation_employee_notified_at IS NULL
                  AND l.assigned_to IS NOT NULL
                  AND l.status = 'open'
                  AND NOW() > l.response_target_at + make_interval(hours => c.escalation_employee_hours)
            """))
            for row in employee_due.mappings().all():
                notif = await create_notification(
                    db, company_id=row["company_id"], notification_type="lead_response_overdue",
                    title="High-priority lead not yet contacted",
                    body=f'"{row["title"]}" is still waiting for first contact.',
                    user_id=row["assigned_to"], data={"lead_id": str(row["id"])},
                )
                await db.execute(
                    text("UPDATE crm_leads SET escalation_employee_notified_at = :now WHERE id = :id"),
                    {"now": now, "id": row["id"]},
                )
                try:
                    publish_notification(str(row["company_id"]), {
                        "id": str(notif.id), "type": "lead_response_overdue",
                        "title": notif.title, "body": notif.body, "user_id": str(row["assigned_to"]),
                    })
                except Exception:
                    log.warning("Failed to publish lead_response_overdue notification", exc_info=True)
            await db.commit()

            manager_due = await db.execute(text("""
                SELECT l.id, l.company_id, l.title, l.assigned_to, c.escalation_manager_hours
                FROM crm_leads l JOIN companies c ON c.id = l.company_id
                WHERE l.priority = 'high'
                  AND l.first_contacted_at IS NULL
                  AND l.response_target_at IS NOT NULL
                  AND l.escalation_manager_notified_at IS NULL
                  AND l.status = 'open'
                  AND NOW() > l.response_target_at + make_interval(hours => c.escalation_manager_hours)
            """))
            for row in manager_due.mappings().all():
                owners = await db.execute(text(
                    "SELECT id FROM users WHERE company_id = :cid AND is_owner = true AND is_active = true"
                ), {"cid": row["company_id"]})
                for (owner_id,) in owners.all():
                    notif = await create_notification(
                        db, company_id=row["company_id"], notification_type="lead_response_overdue_manager",
                        title="Unassigned response: high-priority lead",
                        body=f'"{row["title"]}" has had no first contact well past its response target.',
                        user_id=owner_id, data={"lead_id": str(row["id"])},
                    )
                    try:
                        publish_notification(str(row["company_id"]), {
                            "id": str(notif.id), "type": "lead_response_overdue_manager",
                            "title": notif.title, "body": notif.body, "user_id": str(owner_id),
                        })
                    except Exception:
                        log.warning("Failed to publish manager escalation notification", exc_info=True)
                await db.execute(
                    text("UPDATE crm_leads SET escalation_manager_notified_at = :now WHERE id = :id"),
                    {"now": now, "id": row["id"]},
                )
            await db.commit()

    _run(_escalate())


@celery_app.task(name="app.workers.tasks.send_whatsapp_automation")
def send_whatsapp_automation(log_id: str, template_id: str | None, phone: str, rendered_body: str):
    """Sends one queued WhatsappAutomationLog row via the real Meta API.
    Runs out-of-band (Celery) so the CRM action that fired the rule never
    blocks on, or fails because of, the WhatsApp integration. Never raises
    - failures (e.g. no real Meta credentials configured) are recorded on
    the log row, not surfaced to the caller."""
    import logging

    log = logging.getLogger(__name__)

    async def _send():
        from app.api.v1.endpoints.whatsapp import _call_meta, _get_or_create_contact
        from app.db.session import AsyncSessionLocal
        from app.models.whatsapp import WhatsappAutomationLog, WhatsappMessage, WhatsappTemplate

        from app.core.config import settings
        from app.models.whatsapp import WhatsappAutomationRule

        async with AsyncSessionLocal() as db:
            automation_log = await db.get(WhatsappAutomationLog, log_id)
            if not automation_log:
                return
            rule_row = await db.get(WhatsappAutomationRule, automation_log.rule_id)
            if not rule_row:
                return

            template = await db.get(WhatsappTemplate, template_id) if template_id else None
            try:
                if template:
                    meta_payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "template",
                        "template": {
                            "name": template.name,
                            "language": {"code": template.language},
                        },
                    }
                    message_type = "template"
                    body_for_log = template.body_text
                else:
                    meta_payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {"body": rendered_body},
                    }
                    message_type = "text"
                    body_for_log = rendered_body

                resp_data = await _call_meta(meta_payload)
                wa_message_id = (resp_data.get("messages") or [{}])[0].get("id")

                contact = await _get_or_create_contact(db, rule_row.company_id, phone)
                db.add(WhatsappMessage(
                    company_id=rule_row.company_id,
                    direction="outbound",
                    from_number=settings.WHATSAPP_PHONE_NUMBER_ID,
                    to_number=phone,
                    message_type=message_type,
                    body=body_for_log,
                    status="sent",
                    contact_id=contact.id,
                    wa_message_id=wa_message_id,
                    created_at=datetime.now(timezone.utc),
                ))
                automation_log.status = "sent"
            except Exception as exc:
                automation_log.status = "failed"
                automation_log.error_message = str(exc)
                log.warning("send_whatsapp_automation failed for log_id=%s", log_id, exc_info=True)

            await db.commit()

    _run(_send())


