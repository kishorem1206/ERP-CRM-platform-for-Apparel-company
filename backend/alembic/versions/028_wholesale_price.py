"""ERP Upgrade Phase 1: default wholesale pricing.

- products/product_variants gain a nullable wholesale_price column.
- PricingService.get_price()'s fallback tier now prefers wholesale_price
  over mrp, falling back to mrp only when wholesale_price is null -
  additive, no existing mrp/dealer_price/cost_price usage elsewhere
  changes.

Revision ID: 028_wholesale_price
Revises: 027_whatsapp_automation
"""
from alembic import op

revision = "028_wholesale_price"
down_revision = "027_whatsapp_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS wholesale_price NUMERIC(15, 2)")
    op.execute("ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS wholesale_price NUMERIC(15, 2)")


def downgrade() -> None:
    op.execute("ALTER TABLE product_variants DROP COLUMN IF EXISTS wholesale_price")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS wholesale_price")
