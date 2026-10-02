"""CRM Phase 6: Ad Spend Management — platform ad-metrics fields on
crm_ad_spend (campaign_id, ad_set, impressions, clicks) plus a source
column for future API-import extensibility (manual only for now).

Revision ID: 025_crm_ad_spend_fields
Revises: 024_crm_ad_spend
"""
from alembic import op

revision = "025_crm_ad_spend_fields"
down_revision = "024_crm_ad_spend"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_ad_spend ADD COLUMN IF NOT EXISTS campaign_id VARCHAR(200)")
    op.execute("ALTER TABLE crm_ad_spend ADD COLUMN IF NOT EXISTS ad_set VARCHAR(200)")
    op.execute("ALTER TABLE crm_ad_spend ADD COLUMN IF NOT EXISTS impressions INTEGER")
    op.execute("ALTER TABLE crm_ad_spend ADD COLUMN IF NOT EXISTS clicks INTEGER")
    op.execute("ALTER TABLE crm_ad_spend ADD COLUMN IF NOT EXISTS source VARCHAR(30) NOT NULL DEFAULT 'manual'")


def downgrade() -> None:
    op.execute("ALTER TABLE crm_ad_spend DROP COLUMN IF EXISTS source")
    op.execute("ALTER TABLE crm_ad_spend DROP COLUMN IF EXISTS clicks")
    op.execute("ALTER TABLE crm_ad_spend DROP COLUMN IF EXISTS impressions")
    op.execute("ALTER TABLE crm_ad_spend DROP COLUMN IF EXISTS ad_set")
    op.execute("ALTER TABLE crm_ad_spend DROP COLUMN IF EXISTS campaign_id")
