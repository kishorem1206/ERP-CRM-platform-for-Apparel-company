"""ERP Upgrade Phase 4: Sales Order against customer PO + tolerance.

- sales_orders gains customer_po_number, customer_po_quantity,
  po_tolerance_pct - additive, all nullable (a SO "may" reference a PO,
  per the spec; most won't).
- Enforcement lives in BusinessRulesEngine.validate_po_quantity(), not
  hard-coded into create_sales_order - see business_rules.py.

Revision ID: 030_so_po_reference
Revises: 029_packing_slip_fields
"""
from alembic import op

revision = "030_so_po_reference"
down_revision = "029_packing_slip_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS customer_po_number VARCHAR(100)")
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS customer_po_quantity NUMERIC(15, 4)")
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS po_tolerance_pct NUMERIC(5, 2)")


def downgrade() -> None:
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS po_tolerance_pct")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS customer_po_quantity")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS customer_po_number")
