"""CRM lead assignment: assigned_date/assigned_by/assignment_status, assignment
history table, and a new crm.assign permission.

Revision ID: 020_crm_lead_assign
Revises: 019_style_boxes_fabric
"""
from alembic import op

revision = "020_crm_lead_assign"
down_revision = "019_style_boxes_fabric"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS assigned_date TIMESTAMPTZ")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS assigned_by UUID REFERENCES users(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS assignment_status VARCHAR(20) NOT NULL DEFAULT 'unassigned'")
    op.execute("UPDATE crm_leads SET assignment_status = 'assigned' WHERE assigned_to IS NOT NULL")

    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_assignment_history (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id            UUID NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
            from_assignee_id   UUID REFERENCES users(id) ON DELETE SET NULL,
            to_assignee_id     UUID REFERENCES users(id) ON DELETE SET NULL,
            from_assignee_name VARCHAR(300),
            to_assignee_name   VARCHAR(300),
            changed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
            changed_by_name    VARCHAR(300),
            note               TEXT,
            changed_at         TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_lead_assignment_history_lead_id ON crm_lead_assignment_history(lead_id)")

    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'crm.assign') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT rp.role_id, p.id
        FROM role_permissions rp
        JOIN permissions ep ON ep.id = rp.permission_id AND ep.code = 'crm.edit'
        CROSS JOIN permissions p
        WHERE p.code = 'crm.assign'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'crm.assign')")
    op.execute("DELETE FROM permissions WHERE code = 'crm.assign'")
    op.execute("DROP TABLE IF EXISTS crm_lead_assignment_history")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS assignment_status")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS assigned_by")
    op.execute("ALTER TABLE crm_leads DROP COLUMN IF EXISTS assigned_date")
