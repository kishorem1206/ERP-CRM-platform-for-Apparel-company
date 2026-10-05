"""Upgrade #2 Phase 9: Weight-based Cutting + Piece<->Kg Conversion (spec §9-12).

- production_stage_entries gains input_weight_kg/output_weight_kg/
  wastage_kg/recoverable_kg - opt-in per entry, piece-only entries
  unaffected.
- production_stages gains the same 4 columns as rollup totals, mirroring
  how input_qty/output_qty already roll up from entries.

Revision ID: 040_weight_based_cutting
Revises: 039_grn_excess_delivery
"""
from alembic import op

revision = "040_weight_based_cutting"
down_revision = "039_grn_excess_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("input_weight_kg", "output_weight_kg", "wastage_kg", "recoverable_kg"):
        op.execute(f"ALTER TABLE production_stage_entries ADD COLUMN {col} NUMERIC(10, 3)")
        op.execute(f"ALTER TABLE production_stages ADD COLUMN {col} NUMERIC(10, 3)")


def downgrade() -> None:
    for col in ("recoverable_kg", "wastage_kg", "output_weight_kg", "input_weight_kg"):
        op.execute(f"ALTER TABLE production_stages DROP COLUMN {col}")
        op.execute(f"ALTER TABLE production_stage_entries DROP COLUMN {col}")
