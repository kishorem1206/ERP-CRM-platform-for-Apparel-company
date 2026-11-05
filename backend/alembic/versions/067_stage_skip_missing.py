"""Skipped stages, missing pieces, and closing a lot early.

- production_stages.missing_qty: pieces lost at this stage (gone outside,
  not returned by job work, lost at packing), apart from rejects.
- production_stages.skip_reason: why a stage was bypassed (status "skipped").
- production_stage_entries.missing / production_stage_challans.missing_qty:
  where each missing count was recorded.
- production_lots.closed_early_reason: set when a lot is closed before all
  of its stages are done.

Revision ID: 067_stage_skip_missing
Revises: 066_grn_edit_permission
"""
from alembic import op

revision = "067_stage_skip_missing"
down_revision = "066_grn_edit_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS missing_qty INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS skip_reason TEXT")
    op.execute("ALTER TABLE production_stage_entries ADD COLUMN IF NOT EXISTS missing INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE production_stage_challans ADD COLUMN IF NOT EXISTS missing_qty INTEGER")
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS closed_early_reason TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS closed_early_reason")
    op.execute("ALTER TABLE production_stage_challans DROP COLUMN IF EXISTS missing_qty")
    op.execute("ALTER TABLE production_stage_entries DROP COLUMN IF EXISTS missing")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS skip_reason")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS missing_qty")
