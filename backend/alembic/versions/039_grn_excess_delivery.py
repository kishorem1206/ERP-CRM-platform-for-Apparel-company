"""Upgrade #2 Phase 8: GRN Excess Delivery (spec §6).

- purchase_entry_items.excess_qty - the portion of a GRN item's
  accepted_qty that pushed its linked PO item's cumulative received_qty
  past ordered_qty. None when the GRN item has no po_item_id.

Revision ID: 039_grn_excess_delivery
Revises: 038_mis_return_tracking
"""
from alembic import op

revision = "039_grn_excess_delivery"
down_revision = "038_mis_return_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE purchase_entry_items ADD COLUMN excess_qty NUMERIC(15, 3)")


def downgrade() -> None:
    op.execute("ALTER TABLE purchase_entry_items DROP COLUMN excess_qty")
