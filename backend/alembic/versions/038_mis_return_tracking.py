"""Upgrade #2 Phase 7: MIS Return Tracking (spec §18/§19).

- material_issue_items gains used_qty / returned_qty / wastage_qty and
  return_inv_transaction_id - recorded once the stage's actual
  consumption is known. Returned quantity flows back into real
  inventory via InventoryService.receive() (reference_type=mis_return),
  the same unified inventory principle issue() already uses.

Revision ID: 038_mis_return_tracking
Revises: 037_lot_trim_packing_snapshot
"""
from alembic import op

revision = "038_mis_return_tracking"
down_revision = "037_lot_trim_packing_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE material_issue_items ADD COLUMN used_qty NUMERIC(15, 4)")
    op.execute("ALTER TABLE material_issue_items ADD COLUMN returned_qty NUMERIC(15, 4)")
    op.execute("ALTER TABLE material_issue_items ADD COLUMN wastage_qty NUMERIC(15, 4)")
    op.execute("ALTER TABLE material_issue_items ADD COLUMN return_inv_transaction_id UUID NULL REFERENCES inventory_transactions(id)")
    op.execute("ALTER TABLE material_issue_items ADD COLUMN return_notes TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE material_issue_items DROP COLUMN return_notes")
    op.execute("ALTER TABLE material_issue_items DROP COLUMN return_inv_transaction_id")
    op.execute("ALTER TABLE material_issue_items DROP COLUMN wastage_qty")
    op.execute("ALTER TABLE material_issue_items DROP COLUMN returned_qty")
    op.execute("ALTER TABLE material_issue_items DROP COLUMN used_qty")
