"""kamna changeset phase 2 — job work challans (OUT/IN, bill tracking, outsourcing)

Revision ID: 011_kamna_phase2
Revises: 010_kamna_phase1
Create Date: 2026-09-06

Implements the outsourced-production-stage portion of the "KAMNA CHANGESET" section
of Garments_ERP_Style_Master_Specification.md (§30-36, §47.6-47.8, §47.11, §47.12,
§47.26): a production-side Job Work Challan tracking material sent OUT to a vendor
for a stage and received back IN, with bill/invoice tracking distinct from goods
receipt. This is a new document type — the sales-side `deliveries` model is bound to
a sales_order/customer and is not reusable for production-to-vendor transfers.
"""
from alembic import op

revision = "011_kamna_phase2"
down_revision = "010_kamna_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── production_stage_challans — OUT/IN movement to an outsourced vendor ────
    op.execute("""
        CREATE TABLE IF NOT EXISTS production_stage_challans (
            id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            production_stage_id   UUID NOT NULL REFERENCES production_stages(id) ON DELETE CASCADE,
            challan_number        VARCHAR(50) NOT NULL,
            vendor_id             UUID NOT NULL REFERENCES vendors(id),
            out_date              DATE NOT NULL,
            out_qty               INTEGER NOT NULL,
            in_date               DATE,
            in_qty                INTEGER,
            expected_return_days  INTEGER,
            status                VARCHAR(20) NOT NULL DEFAULT 'out',
            bill_amount           NUMERIC(15,2),
            bill_received         BOOLEAN NOT NULL DEFAULT false,
            bill_received_date    DATE,
            notes                 TEXT,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ,
            created_by            UUID REFERENCES users(id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_production_stage_challans_stage ON production_stage_challans(production_stage_id)")

    # ── document_sequences — seed the job_work_challan document type ──────────
    op.execute("""
        INSERT INTO document_sequences (company_id, document_type, prefix, separator, year_format, next_number, padding)
        SELECT c.id, 'job_work_challan', 'JWC', '/', 'YY', 1, 4
        FROM companies c
        ON CONFLICT (company_id, document_type) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_sequences WHERE document_type = 'job_work_challan'")
    op.execute("DROP TABLE IF EXISTS production_stage_challans")
