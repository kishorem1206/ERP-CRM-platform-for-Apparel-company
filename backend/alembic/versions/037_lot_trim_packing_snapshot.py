"""Upgrade #2 Phase 4: Lot-level Trim/Packing snapshot + size-wise trim consumption.

- style_trim_sizes: optional per-trim size-wise quantity (spec §21),
  meaningful when the parent StyleTrim.category = 'Sizable'.
- lot_trims / lot_packing_materials: LOT-level snapshot of a Style's
  trims/packing materials, auto-fetched at LOT creation, mirroring the
  planned/actual split already used by lot_additional_costs.

Revision ID: 037_lot_trim_packing_snapshot
Revises: 036_size_chart
"""
from alembic import op

revision = "037_lot_trim_packing_snapshot"
down_revision = "036_size_chart"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_trim_sizes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            style_trim_id UUID NOT NULL REFERENCES style_trims(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            quantity NUMERIC(15, 4) NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS lot_trims (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            style_trim_id UUID NULL REFERENCES style_trims(id),
            trim_name VARCHAR(200) NOT NULL,
            unit VARCHAR(30),
            category VARCHAR(30),
            planned_qty NUMERIC(15, 4),
            actual_qty NUMERIC(15, 4),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS lot_packing_materials (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            style_packing_material_id UUID NULL REFERENCES style_packing_materials(id),
            material_name VARCHAR(200) NOT NULL,
            unit VARCHAR(30),
            consumption_stage VARCHAR(50),
            planned_qty NUMERIC(15, 4),
            actual_qty NUMERIC(15, 4),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE lot_packing_materials")
    op.execute("DROP TABLE lot_trims")
    op.execute("DROP TABLE style_trim_sizes")
