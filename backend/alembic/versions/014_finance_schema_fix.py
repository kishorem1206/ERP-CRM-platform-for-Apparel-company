"""finance schema fix — align payments/credit/debit note tables with the ORM models

Revision ID: 014_finance_fix
Revises: 013_kamna_phase4
Create Date: 2026-09-07

The Finance module's models, schemas, services, and endpoints (customer Payment,
VendorPayment, CreditNote, DebitNote) were built against a schema that `db/schema.sql`
never actually provided: `payments` there was vendor-shaped (vendor_id, payment_method,
no status/bank_account), and `vendor_payments`, `payment_allocations`,
`vendor_payment_allocations`, `credit_notes`, `debit_notes` didn't exist at all —
every Finance endpoint 500'd. `receipts`/`receipt_allocations` were an orphaned,
unreferenced predecessor design (no model, no code path uses them) with zero rows,
superseded by `payments`/`payment_allocations`. All affected tables are empty in every
environment this has run in, so this rebuilds them to match `app/models/finance.py`
exactly rather than attempting a data-preserving column migration.
"""
from alembic import op

revision = "014_finance_fix"
down_revision = "013_kamna_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS receipt_allocations")
    op.execute("DROP TABLE IF EXISTS receipts")
    op.execute("DROP TABLE IF EXISTS payments CASCADE")

    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id      UUID NOT NULL REFERENCES companies(id),
            payment_number  VARCHAR(50) NOT NULL,
            customer_id     UUID NOT NULL REFERENCES customers(id),
            payment_date    DATE NOT NULL,
            amount          NUMERIC(15,2) NOT NULL,
            payment_mode    VARCHAR(20) NOT NULL DEFAULT 'neft',
            reference       VARCHAR(100),
            bank_account    VARCHAR(100),
            notes           TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'recorded',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by      UUID REFERENCES users(id),
            UNIQUE (company_id, payment_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            payment_id          UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
            invoice_id          UUID NOT NULL REFERENCES invoices(id),
            allocated_amount    NUMERIC(15,2) NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS vendor_payments (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id      UUID NOT NULL REFERENCES companies(id),
            payment_number  VARCHAR(50) NOT NULL,
            vendor_id       UUID NOT NULL REFERENCES vendors(id),
            payment_date    DATE NOT NULL,
            amount          NUMERIC(15,2) NOT NULL,
            payment_mode    VARCHAR(20) NOT NULL DEFAULT 'neft',
            reference       VARCHAR(100),
            bank_account    VARCHAR(100),
            notes           TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'recorded',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by      UUID REFERENCES users(id),
            UNIQUE (company_id, payment_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS vendor_payment_allocations (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            vendor_payment_id   UUID NOT NULL REFERENCES vendor_payments(id) ON DELETE CASCADE,
            purchase_entry_id   UUID NOT NULL REFERENCES purchase_entries(id),
            allocated_amount    NUMERIC(15,2) NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS credit_notes (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id          UUID NOT NULL REFERENCES companies(id),
            credit_note_number  VARCHAR(50) NOT NULL,
            customer_id         UUID NOT NULL REFERENCES customers(id),
            invoice_id          UUID REFERENCES invoices(id),
            credit_note_date    DATE NOT NULL,
            reason              TEXT,
            taxable_amount      NUMERIC(15,2) NOT NULL DEFAULT 0,
            cgst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
            sgst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
            igst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
            total_amount        NUMERIC(15,2) NOT NULL,
            status              VARCHAR(20) NOT NULL DEFAULT 'issued',
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by          UUID REFERENCES users(id),
            UNIQUE (company_id, credit_note_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS debit_notes (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id          UUID NOT NULL REFERENCES companies(id),
            debit_note_number   VARCHAR(50) NOT NULL,
            vendor_id           UUID NOT NULL REFERENCES vendors(id),
            purchase_entry_id   UUID REFERENCES purchase_entries(id),
            debit_note_date     DATE NOT NULL,
            reason              TEXT,
            total_amount        NUMERIC(15,2) NOT NULL,
            status              VARCHAR(20) NOT NULL DEFAULT 'issued',
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by          UUID REFERENCES users(id),
            UNIQUE (company_id, debit_note_number)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS debit_notes")
    op.execute("DROP TABLE IF EXISTS credit_notes")
    op.execute("DROP TABLE IF EXISTS vendor_payment_allocations")
    op.execute("DROP TABLE IF EXISTS vendor_payments")
    op.execute("DROP TABLE IF EXISTS payment_allocations")
    op.execute("DROP TABLE IF EXISTS payments")
