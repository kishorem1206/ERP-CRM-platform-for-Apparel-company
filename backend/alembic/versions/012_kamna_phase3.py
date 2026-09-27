"""kamna changeset phase 3 — fabric processing, weight-based/colour-split lots

Revision ID: 012_kamna_phase3
Revises: 011_kamna_phase2
Create Date: 2026-09-06

Implements the fabric-side portion of the "KAMNA CHANGESET" section of
Garments_ERP_Style_Master_Specification.md (§47.2-47.5, §47.19-47.21): fabric
processing (dyeing/printing) with input/output weight and gain/loss tracked
separately from garment production, its own rate configuration on Style Fabric,
and weight-based/colour-split LOT batches as additive fields alongside the
existing piece-based ones.
"""
from alembic import op

revision = "012_kamna_phase3"
down_revision = "011_kamna_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── fabric_processing_entries — dyeing/printing weight in/out + gain/loss ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS fabric_processing_entries (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            production_lot_id   UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            process_type        VARCHAR(30) NOT NULL,
            vendor_id           UUID REFERENCES vendors(id),
            in_date             DATE NOT NULL,
            input_kg            NUMERIC(12,3) NOT NULL,
            out_date            DATE,
            output_kg           NUMERIC(12,3),
            gain_loss_kg        NUMERIC(12,3),
            rate_per_kg         NUMERIC(15,2),
            bill_amount         NUMERIC(15,2),
            status              VARCHAR(20) NOT NULL DEFAULT 'in_process',
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ,
            created_by          UUID REFERENCES users(id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fabric_processing_entries_lot ON fabric_processing_entries(production_lot_id)")

    # ── style_fabrics — fabric-processing rate configuration (§47.20) ──────────
    op.execute("ALTER TABLE style_fabrics ADD COLUMN IF NOT EXISTS dyeing_rate NUMERIC(15,2)")
    op.execute("ALTER TABLE style_fabrics ADD COLUMN IF NOT EXISTS printing_rate NUMERIC(15,2)")

    # ── production_lots — weight-based / colour-split batch fields (§47.2) ─────
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS colour_id UUID REFERENCES colours(id)")
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS planned_weight_kg NUMERIC(12,3)")
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS actual_weight_kg NUMERIC(12,3)")


def downgrade() -> None:
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS actual_weight_kg")
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS planned_weight_kg")
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS colour_id")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN IF EXISTS printing_rate")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN IF EXISTS dyeing_rate")
    op.execute("DROP TABLE IF EXISTS fabric_processing_entries")
