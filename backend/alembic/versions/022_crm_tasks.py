"""CRM Phase 3: centralized task system (crm_tasks table).

Revision ID: 022_crm_tasks
Revises: 021_crm_followups
"""
from alembic import op

revision = "022_crm_tasks"
down_revision = "021_crm_followups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_tasks (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id    UUID NOT NULL REFERENCES companies(id),
            title         VARCHAR(500) NOT NULL,
            notes         TEXT,
            lead_id       UUID REFERENCES crm_leads(id) ON DELETE SET NULL,
            customer_id   UUID REFERENCES customers(id) ON DELETE SET NULL,
            assigned_to   UUID REFERENCES users(id) ON DELETE SET NULL,
            due_at        TIMESTAMPTZ,
            priority      VARCHAR(20) NOT NULL DEFAULT 'medium',
            status        VARCHAR(20) NOT NULL DEFAULT 'pending',
            source        VARCHAR(30) NOT NULL DEFAULT 'manual',
            created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
            completed_at  TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_tasks_company_assignee_status ON crm_tasks(company_id, assigned_to, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_tasks_lead_id ON crm_tasks(lead_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_tasks")
