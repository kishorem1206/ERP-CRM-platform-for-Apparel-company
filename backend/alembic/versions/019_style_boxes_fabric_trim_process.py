"""style pieces_per_box + fabric_source, lot pieces_per_box, trim process link

Revision ID: 019_style_boxes_fabric
Revises: 018_actual_selling_price
"""
from alembic import op

revision = "019_style_boxes_fabric"
down_revision = "018_actual_selling_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS pieces_per_box INTEGER")
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS fabric_source VARCHAR(20) NOT NULL DEFAULT 'yarn'")
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS pieces_per_box INTEGER")
    op.execute("ALTER TABLE style_trims ADD COLUMN IF NOT EXISTS process_seq SMALLINT")


def downgrade() -> None:
    op.execute("ALTER TABLE style_trims DROP COLUMN IF EXISTS process_seq")
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS pieces_per_box")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS fabric_source")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS pieces_per_box")
