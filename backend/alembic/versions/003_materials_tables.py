"""materials schema drift — add missing columns and child tables

Revision ID: 003_materials_tables
Revises: 002_b2b_customer_enhancements
Create Date: 2026-08-29

Adds the columns and tables that exist in the ORM but were absent from
prior migrations (bootstrapped directly from schema.sql).  All DDL uses
IF NOT EXISTS so the migration is safe on databases that already have
these objects.
"""
from alembic import op

revision = "003_materials_tables"
down_revision = "002_b2b_customer_enhancements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── inventory_lots — missing columns ──────────────────────────────────────
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS bags           NUMERIC(10,2)")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS kg_per_bag     NUMERIC(10,3)")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS trim_type      VARCHAR(50)")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS trim_unit      VARCHAR(30)")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS split_by_colour BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS split_by_dia   BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS notes          TEXT")

    # ── material_composition_items ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS material_composition_items (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            inventory_lot_id  UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
            fibre_name        VARCHAR(100) NOT NULL,
            percentage        NUMERIC(5,2) NOT NULL,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mci_lot
        ON material_composition_items(inventory_lot_id)
    """)

    # ── fabric_variants ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS fabric_variants (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            inventory_lot_id  UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
            colour            VARCHAR(100),
            dia_inches        NUMERIC(8,2),
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_fv_lot
        ON fabric_variants(inventory_lot_id)
    """)

    # ── trim_variants ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS trim_variants (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            inventory_lot_id  UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
            colour            VARCHAR(100),
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tv_lot
        ON trim_variants(inventory_lot_id)
    """)

    # ── document_sequences — seed material document types ─────────────────────
    op.execute("""
        INSERT INTO document_sequences (company_id, document_type, prefix, separator, year_format, next_number, padding)
        SELECT c.id, dt.document_type, dt.prefix, dt.sep, dt.yf, 1, 4
        FROM companies c
        CROSS JOIN (VALUES
            ('yarn',       'YRN', '-', '%y'),
            ('fabric',     'FAB', '-', '%y'),
            ('trim',       'TRM', '-', '%y'),
            ('fabric_run', 'FR',  '-', '%y')
        ) AS dt(document_type, prefix, sep, yf)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Downgrade intentionally left minimal — drop only the new tables; columns
    # added to inventory_lots are left in place to avoid data loss.
    op.execute("DROP TABLE IF EXISTS trim_variants")
    op.execute("DROP TABLE IF EXISTS fabric_variants")
    op.execute("DROP TABLE IF EXISTS material_composition_items")
