"""backfill stage planned_qty for lots created before the OUT/IN quantity-flow fix

Revision ID: 016_backfill_planned_qty
Revises: 015_out_in_flow
Create Date: 2026-09-07

Migration 015 fixed stage-to-stage quantity propagation going forward, and
backfilled sent_qty/received_qty from the old (backwards) input_qty/output_qty
columns. It did NOT recompute planned_qty on already-existing downstream
stages, because propagation only fires on new events (a new receive, a new
entry, a manual edit) — a stage whose predecessor had already completed
before the fix was deployed never got a new event to trigger it. Those
stages are still carrying the LOT's original planned_qty (the old bug) even
though their predecessor's actual accepted output is now correctly recorded.

This is a one-time data repair: for every stage that is NOT the first stage
in its lot (ordered by created_at, same ordering used everywhere else),
recompute planned_qty from its immediate predecessor's actual accepted
output (received_qty for a vendor/internal_worker stage, output_qty for an
in-house stage) — mirroring _stage_accepted_qty() in
app/services/production.py. A predecessor with 0 accepted output yet (not
started) resets the successor to NULL, matching a freshly-created stage.
Idempotent — safe to run again.
"""
from alembic import op

revision = "016_backfill_planned_qty"
down_revision = "015_out_in_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        WITH ordered AS (
            SELECT
                id,
                LAG(id) OVER (PARTITION BY production_lot_id ORDER BY created_at) AS prev_id,
                LAG(output_qty) OVER (PARTITION BY production_lot_id ORDER BY created_at) AS prev_output_qty,
                LAG(received_qty) OVER (PARTITION BY production_lot_id ORDER BY created_at) AS prev_received_qty,
                LAG(assignment_type) OVER (PARTITION BY production_lot_id ORDER BY created_at) AS prev_assignment_type
            FROM production_stages
        )
        UPDATE production_stages ps
        SET planned_qty = CASE
            WHEN o.prev_assignment_type IS NOT NULL THEN NULLIF(o.prev_received_qty, 0)
            ELSE NULLIF(o.prev_output_qty, 0)
        END
        FROM ordered o
        WHERE ps.id = o.id AND o.prev_id IS NOT NULL
    """)


def downgrade() -> None:
    # Data repair only — not reversible (the pre-repair values were the bug).
    pass
