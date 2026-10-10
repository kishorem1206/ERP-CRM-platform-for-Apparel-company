"""Production Module Reorganisation Phase 3 — Yarn Planning.

Extends StyleYarn so a yarn row can be assigned to compose a specific
StyleFabric row (reference screenshot: "Yarn Planning For [From Yarn]
Fabrics" -> per-fabric "Assign Yarn" with Counts/Yarn Name/Colour/
Consumption %). style_fabric_id is nullable — existing freestanding yarn
rows (not tied to any fabric) keep working exactly as before.

Revision ID: 054_yarn_planning
Revises: 053_fabric_requirement
"""
from alembic import op

revision = "054_yarn_planning"
down_revision = "053_fabric_requirement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE style_yarns ADD COLUMN style_fabric_id UUID REFERENCES style_fabrics(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE style_yarns ADD COLUMN colour_id UUID REFERENCES colours(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE style_yarns ADD COLUMN counts VARCHAR(20)")
    op.execute("ALTER TABLE style_yarns ADD COLUMN consumption_pct NUMERIC(5, 2)")
    op.execute("CREATE INDEX ix_style_yarns_fabric ON style_yarns(style_fabric_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE style_yarns DROP COLUMN consumption_pct")
    op.execute("ALTER TABLE style_yarns DROP COLUMN counts")
    op.execute("ALTER TABLE style_yarns DROP COLUMN colour_id")
    op.execute("ALTER TABLE style_yarns DROP COLUMN style_fabric_id")
