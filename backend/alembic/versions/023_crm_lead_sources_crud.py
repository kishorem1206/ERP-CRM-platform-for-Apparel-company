"""CRM Phase 4: make lead sources/platforms configurable — unique constraint
to support rename/create dedupe, plus seed the spec's missing platform
values (WhatsApp, Instagram, Facebook, Google, Direct).

Revision ID: 023_crm_lead_sources
Revises: 022_crm_tasks
"""
from alembic import op

revision = "023_crm_lead_sources"
down_revision = "022_crm_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guard against pre-existing duplicate (company_id, name) rows before
    # adding the unique constraint (none expected today, but safe either way).
    op.execute("""
        DELETE FROM crm_lead_sources a
        USING crm_lead_sources b
        WHERE a.id > b.id
          AND a.company_id = b.company_id
          AND a.name = b.name
    """)
    op.execute("""
        ALTER TABLE crm_lead_sources
        ADD CONSTRAINT uq_crm_lead_sources_company_name UNIQUE (company_id, name)
    """)
    op.execute("""
        INSERT INTO crm_lead_sources (id, company_id, name)
        SELECT gen_random_uuid(), c.id, s
        FROM companies c
        CROSS JOIN (VALUES ('WhatsApp'), ('Instagram'), ('Facebook'), ('Google'), ('Direct')) AS v(s)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE crm_lead_sources DROP CONSTRAINT IF EXISTS uq_crm_lead_sources_company_name")
    op.execute("DELETE FROM crm_lead_sources WHERE name IN ('WhatsApp', 'Instagram', 'Facebook', 'Google', 'Direct')")
