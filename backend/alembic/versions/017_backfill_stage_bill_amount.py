"""backfill production_stages.bill_amount with the corrected rate-priority formula

Revision ID: 017_backfill_bill_amount
Revises: 016_backfill_planned_qty
Create Date: 2026-09-07

_stage_actual_cost() in app/services/production.py briefly (within this same
session) prioritized a stage's challan bill total over its rate_per_pc ×
accepted-qty estimate. That was backwards: a configured rate_per_pc is the
agreed per-piece billing basis and must win when present (e.g. Rate/Pc ₹20 ×
448 accepted = ₹8,960 must be the actual cost, not a stale/unrelated ₹900
entered on one challan's bill_amount field). The formula has been corrected;
this is a one-time repair of the stored production_stages.bill_amount column
for stages that were already written under the wrong priority before the fix
(the stage card displays this stored value directly; it only self-heals on
the next write to that stage, so already-completed stages need this
backfill). Idempotent — safe to run again; matches _stage_actual_cost() and
the write-path guard exactly (only touches stages with a rate or a challan
bill; stages with neither keep bill_amount NULL).
"""
from alembic import op

revision = "017_backfill_bill_amount"
down_revision = "016_backfill_planned_qty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE production_stages ps
        SET bill_amount = CASE
            WHEN ps.rate_per_pc IS NOT NULL THEN
                ps.rate_per_pc * (CASE WHEN ps.assignment_type IS NOT NULL THEN ps.received_qty ELSE ps.output_qty END)
            ELSE (
                SELECT COALESCE(SUM(psc.bill_amount), 0)
                FROM production_stage_challans psc
                WHERE psc.production_stage_id = ps.id
            )
        END
        WHERE ps.rate_per_pc IS NOT NULL
           OR EXISTS (
               SELECT 1 FROM production_stage_challans psc
               WHERE psc.production_stage_id = ps.id AND psc.bill_amount IS NOT NULL
           )
    """)


def downgrade() -> None:
    # Data repair only — not reversible (the pre-repair values were the bug).
    pass
