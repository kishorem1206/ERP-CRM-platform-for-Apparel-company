"""CRM Phase 5: lead acquisition cost — crm_ad_spend table (platform,
campaign, spend amount, date range).

Revision ID: 024_crm_ad_spend
Revises: 023_crm_lead_sources
"""
from alembic import op

revision = "024_crm_ad_spend"
down_revision = "023_crm_lead_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_ad_spend (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id    UUID NOT NULL REFERENCES companies(id),
            source_id     UUID REFERENCES crm_lead_sources(id) ON DELETE SET NULL,
            campaign      VARCHAR(200),
            period_start  DATE NOT NULL,
            period_end    DATE NOT NULL,
            amount        NUMERIC(15, 2) NOT NULL,
            notes         TEXT,
            created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_ad_spend_company_source_period ON crm_ad_spend(company_id, source_id, period_start)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_ad_spend")
