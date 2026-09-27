"""kamna changeset phase 1 — style target price, fabric GSM, additional costs / agent commission

Revision ID: 010_kamna_phase1
Revises: 009_style_master
Create Date: 2026-09-06

Implements the Style-level portion of the "KAMNA CHANGESET" section of
Garments_ERP_Style_Master_Specification.md (§47.14, §47.18, §47.19, §47.22, §47.28):
a Style-level Target Price that flows into new LOTs as the default, a GSM
attribute on Style Fabric rows, and a shared Additional-Costs / Agent-Commission
mechanism at both Style (planned) and LOT (planned + actual) level.
"""
from alembic import op

revision = "010_kamna_phase1"
down_revision = "009_style_master"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── styles — Target Price baseline (distinct from actual production cost) ─
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS target_price NUMERIC(15,2)")

    # ── style_fabrics — GSM as a first-class fabric attribute ─────────────────
    op.execute("ALTER TABLE style_fabrics ADD COLUMN IF NOT EXISTS gsm NUMERIC(8,2)")

    # ── style_additional_costs — Additional Costs & Agent Commission (planned) ─
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_additional_costs (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id          UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            cost_type         VARCHAR(30) NOT NULL DEFAULT 'additional',
            description       VARCHAR(200) NOT NULL,
            amount            NUMERIC(15,2),
            basis             VARCHAR(30),
            party_vendor_id   UUID REFERENCES vendors(id),
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_additional_costs_style ON style_additional_costs(style_id)")

    # ── lot_additional_costs — snapshot at LOT creation, with actual recorded ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS lot_additional_costs (
            id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            production_lot_id         UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            style_additional_cost_id  UUID REFERENCES style_additional_costs(id),
            cost_type                 VARCHAR(30) NOT NULL DEFAULT 'additional',
            description               VARCHAR(200) NOT NULL,
            planned_amount            NUMERIC(15,2),
            actual_amount             NUMERIC(15,2),
            basis                     VARCHAR(30),
            party_vendor_id           UUID REFERENCES vendors(id),
            notes                     TEXT,
            created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at                TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_lot_additional_costs_lot ON lot_additional_costs(production_lot_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lot_additional_costs")
    op.execute("DROP TABLE IF EXISTS style_additional_costs")
    op.execute("ALTER TABLE style_fabrics DROP COLUMN IF EXISTS gsm")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS target_price")
