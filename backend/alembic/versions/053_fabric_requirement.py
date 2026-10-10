"""Production Module Reorganisation Phase 2 — Fabric Requirement/Planning.

Extends StyleFabric (previously a single flat row per fabric, no part/size
breakdown) to match the reference screenshots' Fabric Requirement screen:
- style_part_id: fabric-to-(style/body)-part mapping, reusing the same
  StylePart master from Phase 1 (see Phase 1's open question about whether
  "Style Part" and "Body Part" are the same master — treated as one here).
- colour_id: explicit fabric colour, independent of the part's own colour
  (e.g. a white fabric later dyed to match a red part).
- source_type: "yarn" or "purchased" per fabric row — a style's own
  fabric_source is the default sourcing, but the screenshots show this can
  be overridden per fabric row (NULL = inherit from the style).
- knit_dia / finish_dia: fabric roll diameter planning.
- style_fabric_sizes: size-wise consumption (mirrors style_trim_sizes) —
  absence of rows means the flat `consumption` figure applies uniformly,
  exactly like StyleTrim's existing size-breakdown convention.

All additive and nullable; existing styles/fabrics are unaffected.

Revision ID: 053_fabric_requirement
Revises: 052_style_parts
"""
from alembic import op

revision = "053_fabric_requirement"
down_revision = "052_style_parts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE style_fabrics ADD COLUMN style_part_id UUID REFERENCES style_parts(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE style_fabrics ADD COLUMN colour_id UUID REFERENCES colours(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE style_fabrics ADD COLUMN source_type VARCHAR(20)")
    op.execute("ALTER TABLE style_fabrics ADD COLUMN knit_dia NUMERIC(8, 2)")
    op.execute("ALTER TABLE style_fabrics ADD COLUMN finish_dia NUMERIC(8, 2)")
    op.execute("""
        CREATE TABLE style_fabric_sizes (
            id UUID PRIMARY KEY,
            style_fabric_id UUID NOT NULL REFERENCES style_fabrics(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            quantity NUMERIC(15, 4),
            sort_order SMALLINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX ix_style_fabric_sizes_fabric ON style_fabric_sizes(style_fabric_id)")


def downgrade() -> None:
    op.execute("DROP TABLE style_fabric_sizes")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN finish_dia")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN knit_dia")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN source_type")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN colour_id")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN style_part_id")
