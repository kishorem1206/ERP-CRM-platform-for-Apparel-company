"""Upgrade #2 Phase 11: configurable bill/invoice alert window (spec §32).

Revision ID: 041_bill_alert_days
Revises: 040_weight_based_cutting
"""
from alembic import op

revision = "041_bill_alert_days"
down_revision = "040_weight_based_cutting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE companies ADD COLUMN bill_alert_days SMALLINT NOT NULL DEFAULT 7")


def downgrade() -> None:
    op.execute("ALTER TABLE companies DROP COLUMN bill_alert_days")
