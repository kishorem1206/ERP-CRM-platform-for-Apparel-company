"""Production Module Reorganisation Phase 9 — Cutting, Checking, Packing
and Completed.

The aggregate stage-to-stage quantity flow (ProductionStage.input_qty/
output_qty/accepted_qty, already correctly propagated stage-to-stage by
_propagate_to_next_stage) remains the system of record — this migration
does not touch it. It adds size-wise detail alongside it:
production_stage_sizes mirrors ProductionLotSize, scoped per stage instead
of per lot, carrying accepted/rejected/rework quantities and a defect
reason per size — the size-wise "Checked/Accepted/Rejected/Rework/Pending"
and "size-wise cut quantity" the spec wants, recorded explicitly by floor
staff rather than auto-derived (that would require rewiring the existing
challan/manual-entry rollup paths — a larger, separate change; see the
Phase 9 report for the explicit scoping decision).

Revision ID: 060_stage_size_tracking
Revises: 059_lot_part_quantities
"""
from alembic import op

revision = "060_stage_size_tracking"
down_revision = "059_lot_part_quantities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE production_stage_sizes (
            id UUID PRIMARY KEY,
            production_stage_id UUID NOT NULL REFERENCES production_stages(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            input_qty INTEGER NOT NULL DEFAULT 0,
            accepted_qty INTEGER NOT NULL DEFAULT 0,
            rejected_qty INTEGER NOT NULL DEFAULT 0,
            rework_qty INTEGER NOT NULL DEFAULT 0,
            defect_reason VARCHAR(200),
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE UNIQUE INDEX ux_production_stage_sizes_stage_size ON production_stage_sizes(production_stage_id, size_id)")


def downgrade() -> None:
    op.execute("DROP TABLE production_stage_sizes")
