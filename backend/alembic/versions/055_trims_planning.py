"""Production Module Reorganisation Phase 4 — Trims Planning.

Adds the same two fields to StyleTrim that Fabric (Phase 2) and Yarn
(Phase 3) already gained: a link to the part it belongs to (a collar may
use a different trim than the shirt front) and an explicit trim colour
(independent of the linked lot). Everything else Phase 4 asks for —
sizeable/non-sizeable category, size-wise consumption, UOM, wastage % —
already existed on StyleTrim before this phase.

Revision ID: 055_trims_planning
Revises: 054_yarn_planning
"""
from alembic import op

revision = "055_trims_planning"
down_revision = "054_yarn_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE style_trims ADD COLUMN style_part_id UUID REFERENCES style_parts(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE style_trims ADD COLUMN colour_id UUID REFERENCES colours(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE style_trims DROP COLUMN colour_id")
    op.execute("ALTER TABLE style_trims DROP COLUMN style_part_id")
