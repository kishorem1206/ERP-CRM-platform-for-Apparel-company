"""Brand master usable from Style creation and material lots.

Product.brand_id already existed (column only, nothing wired to it anywhere).
This adds the same brand_id link to styles and inventory_lots so a Brand,
once created, is one list reused everywhere instead of free text typed
separately per screen — the same "link instead of duplicate" fix already
applied to inventory_lots.product_id in migration history.

Revision ID: 048_brand_links
Revises: 047_pipeline_qualification_stage
"""
from alembic import op

revision = "048_brand_links"
down_revision = "047_pipeline_qualification_stage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE styles ADD COLUMN brand_id UUID REFERENCES brands(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN brand_id UUID REFERENCES brands(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE inventory_lots DROP COLUMN brand_id")
    op.execute("ALTER TABLE styles DROP COLUMN brand_id")
