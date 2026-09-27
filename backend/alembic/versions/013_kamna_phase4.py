"""kamna changeset phase 4 — quality tracking (first quality vs rejected) & cost summary

Revision ID: 013_kamna_phase4
Revises: 012_kamna_phase3
Create Date: 2026-09-06

Implements the final-quality and cost-summary portion of the "KAMNA CHANGESET"
section of Garments_ERP_Style_Master_Specification.md (§37-42, §47.13,
§47.15-47.18): a LOT's finished-goods output now records rejected pieces
alongside first-quality received quantity, and a deterministic cost-summary
aggregation (computed, not persisted) surfaces Total Cost, Cost per
First-Quality Piece, and missing-rate warnings. Only one column is added —
the cost summary itself is pure computation over data already captured in
Phases 1-3.
"""
from alembic import op

revision = "013_kamna_phase4"
down_revision = "012_kamna_phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE production_outputs ADD COLUMN IF NOT EXISTS rejected_qty NUMERIC(15,4)")


def downgrade() -> None:
    op.execute("ALTER TABLE production_outputs DROP COLUMN IF EXISTS rejected_qty")
