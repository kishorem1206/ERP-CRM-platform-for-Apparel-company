"""ERP Upgrade Phase 6: unified Stock Adjustment (Add/Reduce/Replace) +
Transfer hardening.

- inventory_transactions gains previous_balance/new_balance (populated
  only for adjustment-type rows, per the spec's own §8-specific wording -
  not retrofitted onto receive/issue/transfer), adjustment_type
  (add|reduce|replace), and transfer_group_id (shared UUID stamped on
  both sides of a transfer so they remain traceable as one movement,
  per §9).

Revision ID: 031_stock_adjustment_unify
Revises: 030_so_po_reference
"""
from alembic import op

revision = "031_stock_adjustment_unify"
down_revision = "030_so_po_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS previous_balance NUMERIC(15, 4)")
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS new_balance NUMERIC(15, 4)")
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS adjustment_type VARCHAR(10)")
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS transfer_group_id UUID")


def downgrade() -> None:
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN IF EXISTS transfer_group_id")
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN IF EXISTS adjustment_type")
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN IF EXISTS new_balance")
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN IF EXISTS previous_balance")
