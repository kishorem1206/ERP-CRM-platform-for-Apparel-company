"""B2B customer management enhancements

Revision ID: 002_b2b_customer
Revises: 001_initial
Create Date: 2026-08-29

Adds extended fields to customers, timestamps to customer_contacts,
creates nature_of_business and customer_details tables.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002_b2b_customer"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── nature_of_business master table ────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS nature_of_business (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name        VARCHAR(200) NOT NULL UNIQUE,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order  SMALLINT NOT NULL DEFAULT 0
        )
    """)

    op.execute("""
        INSERT INTO nature_of_business (name, sort_order) VALUES
            ('Manufacturer',        10),
            ('Trader / Wholesaler', 20),
            ('Retailer',            30),
            ('Exporter',            40),
            ('Importer',            50),
            ('Service Provider',    60),
            ('Individual',          70),
            ('Other',               99)
        ON CONFLICT (name) DO NOTHING
    """)

    # ── customer_details repeatable rows ────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS customer_details (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            label       VARCHAR(200),
            value       TEXT,
            sort_order  SMALLINT NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_customer_details_customer_id ON customer_details(customer_id)")

    # ── extend customers table ─────────────────────────────────────────────
    # Identity / display
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS print_name VARCHAR(300)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS internal_id VARCHAR(50)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS location VARCHAR(200)")

    # Contact
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS mobile VARCHAR(20)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS whatsapp_no VARCHAR(20)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS landline_no VARCHAR(30)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS email VARCHAR(200)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS contact_person_name VARCHAR(200)")

    # Classification
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS nature_of_business_id UUID REFERENCES nature_of_business(id)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS contact_type VARCHAR(50)")  # e.g. 'buyer','agent'

    # Accounting
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS payable_opening_balance NUMERIC(15,2) DEFAULT 0")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS receivable_opening_balance NUMERIC(15,2) DEFAULT 0")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2) DEFAULT 0")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS tds_percent NUMERIC(5,2) DEFAULT 0")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS enable_tcs BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS due_days SMALLINT DEFAULT 0")

    # Relationships
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS accounts_manager_id UUID REFERENCES users(id)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS agent_id UUID REFERENCES users(id)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS agent_commission_percent NUMERIC(5,2) DEFAULT 0")

    # CRM
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_rating SMALLINT DEFAULT 0")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS other_details TEXT")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS remarks TEXT")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_portal_enabled BOOLEAN DEFAULT FALSE")

    # ── add timestamps to customer_contacts ────────────────────────────────
    op.execute("ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
    op.execute("ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")

    # ── indexes ────────────────────────────────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_mobile ON customers(mobile) WHERE mobile IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email) WHERE email IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_nature_of_business_id ON customers(nature_of_business_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_accounts_manager_id ON customers(accounts_manager_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_agent_id ON customers(agent_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_details CASCADE")
    op.execute("DROP TABLE IF EXISTS nature_of_business CASCADE")
    # Column drops omitted for safety — run manually if truly reverting
