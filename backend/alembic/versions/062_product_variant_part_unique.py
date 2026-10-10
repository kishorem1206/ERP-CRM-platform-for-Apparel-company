"""Fix: product_variants uniqueness must account for style_part_id.

Found while end-to-end testing the Production module with realistic data:
creating a shirt with two style parts sharing the same colour (e.g. Collar
and Cuff both Navy Blue) crashed `_ensure_part_variants`
(app/services/production.py:581-618) with a UniqueViolationError. That
function's own in-memory de-duplication is already correctly keyed by
`(style_part_id, size_id, colour_id)` — the bug is that the DATABASE
constraint added back in 052_style_parts (which only ADDED the
`style_part_id` column) was never widened to match: it was, and still is,
`UNIQUE (product_id, colour_id, size_id)`, so two different parts with the
same colour+size collide even though they're logically distinct
part-level variants ("Collar-S-Navy" vs "Cuff-S-Navy").

Fix: replace the plain unique constraint with a unique index that treats
NULL `style_part_id` as a single sentinel value via COALESCE — this keeps
the original guarantee intact for whole-garment (non-part) products
(still exactly one variant per product+colour+size when style_part_id is
NULL for all of them), while correctly allowing one variant per
product+colour+size+part when parts are used.

Revision ID: 062_product_variant_part_unique
Revises: 061_delivery_returns_ageing
"""
from alembic import op

revision = "062_product_variant_part_unique"
down_revision = "061_delivery_returns_ageing"
branch_labels = None
depends_on = None

_SENTINEL = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.execute("ALTER TABLE product_variants DROP CONSTRAINT product_variants_product_id_colour_id_size_id_key")
    op.execute(f"""
        CREATE UNIQUE INDEX ux_product_variants_product_colour_size_part
        ON product_variants (product_id, colour_id, size_id, COALESCE(style_part_id, '{_SENTINEL}'::uuid))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX ux_product_variants_product_colour_size_part")
    op.execute("ALTER TABLE product_variants ADD CONSTRAINT product_variants_product_id_colour_id_size_id_key UNIQUE (product_id, colour_id, size_id)")
