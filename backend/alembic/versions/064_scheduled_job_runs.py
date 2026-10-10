"""Scheduled job bookkeeping, replacing Celery beat.

One row per job in app.workers.jobs.SCHEDULE: when it last started and
finished, and how it went. POST /api/v1/internal/cron/tick reads this to
decide which jobs are due, so the external trigger (Cloudflare Worker Cron)
can fire on a single fixed interval.

Revision ID: 064_scheduled_job_runs
Revises: 063_production_audit_log
"""
from alembic import op

revision = "064_scheduled_job_runs"
down_revision = "063_production_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE scheduled_job_runs (
            job_name VARCHAR(100) PRIMARY KEY,
            last_started_at TIMESTAMPTZ,
            last_finished_at TIMESTAMPTZ,
            last_status VARCHAR(20),
            last_error TEXT,
            last_duration_ms INTEGER
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE scheduled_job_runs")
