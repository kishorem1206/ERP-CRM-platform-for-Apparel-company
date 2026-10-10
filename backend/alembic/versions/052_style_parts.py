"""Production Module Reorganisation Phase 1 — Style Part foundation.

Style Part Master (e.g. Front/Back/Collar for a shirt, Waistband/Fly for a
trouser) is a new, reusable, company-scoped master, entirely additive:
existing styles with no parts configured keep working exactly as before
(all part_id columns are nullable; no backfill).

- style_parts: the reusable master (dropdown + inline "+ Add New Style
  Part", per the reference screenshots).
- style_part_colours: which colour(s) a given style's part comes in —
  mirrors style_colours but scoped per part. colour_id is nullable (a part
  can be configured before its colour is decided).
- style_part_sizes: per-size planned quantity for one (style, part,
  colour) combination — mirrors style_sizes/production_lot_sizes.
- product_variants.style_part_id: optional SKU segment so
  CODE-PART-SIZE-COLOUR can coexist with the existing CODE-SIZE-COLOUR
  format for styles that don't use parts.

Revision ID: 052_style_parts
Revises: 051_mistake_log
"""
from alembic import op

revision = "052_style_parts"
down_revision = "051_mistake_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE style_parts (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL REFERENCES companies(id),
            name VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE style_part_colours (
            id UUID PRIMARY KEY,
            style_id UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            style_part_id UUID NOT NULL REFERENCES style_parts(id),
            colour_id UUID REFERENCES colours(id),
            sort_order SMALLINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_style_part_colours_style ON style_part_colours(style_id)")
    op.execute("""
        CREATE TABLE style_part_sizes (
            id UUID PRIMARY KEY,
            style_part_colour_id UUID NOT NULL REFERENCES style_part_colours(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            quantity NUMERIC(15, 4),
            sort_order SMALLINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX ix_style_part_sizes_part_colour ON style_part_sizes(style_part_colour_id)")
    op.execute("ALTER TABLE product_variants ADD COLUMN style_part_id UUID REFERENCES style_parts(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE product_variants DROP COLUMN style_part_id")
    op.execute("DROP TABLE style_part_sizes")
    op.execute("DROP TABLE style_part_colours")
    op.execute("DROP TABLE style_parts")
