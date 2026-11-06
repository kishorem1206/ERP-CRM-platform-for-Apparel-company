"""TDS % on additional costs / agent commission; style part sizes as grams.

- style_additional_costs / lot_additional_costs.tds_pct: tax deducted at
  source when paying the agent or contractor. The lot cost stays the full
  amount; the lot shows what's paid to the party and what goes to TDS.
- Style part size values are grams per piece (for that part and size), not
  a piece count. lot_part_sizes gets weight_g (copied from the style) and
  its planned_qty becomes the lot's pieces for that size, so a lot can show
  the total weight each part needs. Existing lots are re-derived that way.

Revision ID: 073_tds_part_weights
Revises: 072_value_unpriced_stock
"""
import sqlalchemy as sa
from alembic import op

revision = "073_tds_part_weights"
down_revision = "072_value_unpriced_stock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("style_additional_costs", sa.Column("tds_pct", sa.Numeric(5, 2)))
    op.add_column("lot_additional_costs", sa.Column("tds_pct", sa.Numeric(5, 2)))
    op.add_column("lot_part_sizes", sa.Column("weight_g", sa.Numeric(12, 3)))
    op.execute("""
        UPDATE lot_part_sizes lps
        SET weight_g = sps.quantity
        FROM lot_part_colours lpc, style_part_sizes sps
        WHERE lpc.id = lps.lot_part_colour_id
          AND sps.style_part_colour_id = lpc.style_part_colour_id
          AND sps.size_id = lps.size_id
    """)
    op.execute("""
        UPDATE lot_part_sizes lps
        SET planned_qty = pls.planned_qty
        FROM lot_part_colours lpc, production_lot_sizes pls
        WHERE lpc.id = lps.lot_part_colour_id
          AND pls.production_lot_id = lpc.production_lot_id
          AND pls.size_id = lps.size_id
    """)


def downgrade() -> None:
    op.drop_column("lot_part_sizes", "weight_g")
    op.drop_column("lot_additional_costs", "tds_pct")
    op.drop_column("style_additional_costs", "tds_pct")
