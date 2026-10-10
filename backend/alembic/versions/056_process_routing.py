"""Production Module Reorganisation Phase 5 — Life Cycle, Process Routing
and Tolerance.

Most of this phase already existed before today: StyleProcess already
supports configurable, non-hardcoded routing with per-process tolerance_pct
and rate bands; ProductionStage already snapshots that tolerance and
computes real variance/within_tolerance against actual input/output
weight (see _stage_out in api/v1/endpoints/production.py); QuantityValidationError
already enforces "output cannot exceed input" and "wastage+recoverable
cannot exceed the unaccounted remainder" at stage-entry time.

The one real gap, matching the Fabric/Yarn/Trim pattern from Phases 2-4:
process routing can now be scoped to a specific Style Part (a collar may
skip a process the front goes through). Nullable and additive.

Revision ID: 056_process_routing
Revises: 055_trims_planning
"""
from alembic import op

revision = "056_process_routing"
down_revision = "055_trims_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE style_processes ADD COLUMN style_part_id UUID REFERENCES style_parts(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE style_processes DROP COLUMN style_part_id")
