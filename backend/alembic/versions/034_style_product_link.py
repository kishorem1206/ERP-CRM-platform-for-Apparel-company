"""Upgrade #2 Phase 1: Style <-> Product/SKU master link.

- styles.product_id (nullable FK to products) - the real sellable
  product behind a Style; NULL for all pre-existing styles (never
  retroactively force-linked).
- production_outputs.variant_id (nullable FK to product_variants) - lets
  a finished-goods receipt record the exact size/colour SKU, additive
  alongside the existing required product_id.

Revision ID: 034_style_product_link
Revises: 033_inventory_value_permission
"""
from alembic import op

revision = "034_style_product_link"
down_revision = "033_inventory_value_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE styles ADD COLUMN product_id UUID NULL REFERENCES products(id)")
    op.execute("ALTER TABLE production_outputs ADD COLUMN variant_id UUID NULL REFERENCES product_variants(id)")


def downgrade() -> None:
    op.execute("ALTER TABLE production_outputs DROP COLUMN variant_id")
    op.execute("ALTER TABLE styles DROP COLUMN product_id")
