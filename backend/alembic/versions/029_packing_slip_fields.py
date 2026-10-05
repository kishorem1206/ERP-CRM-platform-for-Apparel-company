"""ERP Upgrade Phase 3: packing slip fields on deliveries.

- deliveries gains carton_count, package_count, packing_marks,
  gross_weight, net_weight - additive, header-level (same tier as the
  existing transporter/lr_number/vehicle_number dispatch fields).
- Delivery stays the single entity (no parallel "packing slip" table);
  the packing slip is a printable document generated from a Delivery.

Revision ID: 029_packing_slip_fields
Revises: 028_wholesale_price
"""
from alembic import op

revision = "029_packing_slip_fields"
down_revision = "028_wholesale_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS carton_count INTEGER")
    op.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS package_count INTEGER")
    op.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS packing_marks TEXT")
    op.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS gross_weight NUMERIC(10, 3)")
    op.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS net_weight NUMERIC(10, 3)")


def downgrade() -> None:
    op.execute("ALTER TABLE deliveries DROP COLUMN IF EXISTS net_weight")
    op.execute("ALTER TABLE deliveries DROP COLUMN IF EXISTS gross_weight")
    op.execute("ALTER TABLE deliveries DROP COLUMN IF EXISTS packing_marks")
    op.execute("ALTER TABLE deliveries DROP COLUMN IF EXISTS package_count")
    op.execute("ALTER TABLE deliveries DROP COLUMN IF EXISTS carton_count")
