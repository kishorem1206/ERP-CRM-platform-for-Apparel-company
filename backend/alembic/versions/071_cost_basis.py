"""Additional cost / agent commission basis: lump sum, per piece or percent.

basis was free text ("per_piece", "per_pc", "% of FOB", "flat", blank) and a
lot planned the style's number as a flat total whatever it said. It's now
one of lumpsum / per_piece / percent (of selling value = target price x
pieces), and a lot keeps the entered `rate` it worked its amount out from.
Existing lot amounts are left as they are (rate stays NULL): some lot lines
marked per piece already hold totals.

Revision ID: 071_cost_basis
Revises: 070_vendor_contacts_types
"""
import sqlalchemy as sa
from alembic import op

revision = "071_cost_basis"
down_revision = "070_vendor_contacts_types"
branch_labels = None
depends_on = None

_NORMALISE = """
    UPDATE {table} SET basis = CASE
        WHEN basis ILIKE '%\\%%' OR basis ILIKE '%percent%' THEN 'percent'
        WHEN basis ILIKE '%piece%' OR basis ILIKE '%pc%' THEN 'per_piece'
        ELSE 'lumpsum'
    END
"""


def upgrade() -> None:
    op.add_column("lot_additional_costs", sa.Column("rate", sa.Numeric(15, 4)))
    op.execute(_NORMALISE.format(table="style_additional_costs"))
    op.execute(_NORMALISE.format(table="lot_additional_costs"))


def downgrade() -> None:
    op.drop_column("lot_additional_costs", "rate")
