"""CRM follow-up management: next_follow_up_at and related fields on
crm_leads, a configurable crm_follow_up_types lookup table, seeded per
company.

Revision ID: 021_crm_followups
Revises: 020_crm_lead_assign
"""
from alembic import op

revision = "021_crm_followups"
down_revision = "020_crm_lead_assign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS next_follow_up_at TIMESTAMPTZ")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS follow_up_type VARCHAR(100)")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS follow_up_reason TEXT")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS follow_up_notes TEXT")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS follow_up_status VARCHAR(20) NOT NULL DEFAULT 'none'")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS last_contacted_at TIMESTAMPTZ")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS contact_outcome VARCHAR(300)")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS next_action VARCHAR(300)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_follow_up_types (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            name       VARCHAR(200) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        INSERT INTO crm_follow_up_types (id, company_id, name)
        SELECT gen_random_uuid(), c.id, t
        FROM companies c
        CROSS JOIN (VALUES
            ('Phone Call'), ('Email'), ('Meeting'), ('WhatsApp'),
            ('Catalogue Sent'), ('Quotation Sent'), ('Sample Sent'),
            ('Price Discussion'), ('Payment Discussion'),
            ('Note'), ('Task'), ('Other')
        ) AS s(t)
        ON CONFLICT DO NOTHING
    """)

    # Backfill: any lead that already has an open, scheduled activity gets
    # its forward-looking fields synced so existing data isn't left blank.
    op.execute("""
        UPDATE crm_leads l
        SET next_follow_up_at = a.schedule_from,
            follow_up_type = a.type,
            follow_up_reason = a.comment,
            follow_up_status = 'scheduled'
        FROM (
            SELECT DISTINCT ON (lead_id) lead_id, schedule_from, type, comment
            FROM crm_activities
            WHERE lead_id IS NOT NULL AND is_done = false AND schedule_from IS NOT NULL
            ORDER BY lead_id, schedule_from ASC
        ) a
        WHERE a.lead_id = l.id
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_follow_up_types")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS next_action")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS contact_outcome")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS last_contacted_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS follow_up_status")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS follow_up_notes")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS follow_up_reason")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS follow_up_type")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS next_follow_up_at")
