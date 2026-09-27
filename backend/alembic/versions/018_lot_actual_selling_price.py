"""production_lots.actual_selling_price — manually-set actual price, syncs to Product MRP

Revision ID: 018_actual_selling_price
Revises: 017_backfill_bill_amount
Create Date: 2026-09-07

Lets a user record the actual price a lot's output was/will be sold at —
distinct from target_sp (the pre-production target) — as the highest-priority
source in the actual-selling-price hierarchy, and pushed onto the produced
Product(s)' MRP so Inventory > Products reflects it automatically (see
ProductionService.sync_product_pricing in app/services/production.py).
"""
from alembic import op

revision = "018_actual_selling_price"
down_revision = "017_backfill_bill_amount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS actual_selling_price NUMERIC(15,2)")


def downgrade() -> None:
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS actual_selling_price")
