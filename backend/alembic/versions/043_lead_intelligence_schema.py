"""Lead Intelligence Phase 1: normalized intake + scoring + duplicate detection columns on crm_leads.

- source_lead_id, received_at, raw_source_data, normalized_data: normalized
  lead intake (spec Step 2) - raw payload is kept, never discarded, so
  integration problems stay debuggable.
- score, priority, score_version, score_breakdown, scored_at: scoring engine
  output (spec Steps 14-16, 21) - breakdown + version kept so a score stays
  explainable and reproducible even after scoring rules change later.
- duplicate_status, duplicate_of_lead_id, is_repeat_contact: duplicate /
  repeat-contact detection (spec Steps 11-12).
- companies.lead_score_high_threshold / lead_score_medium_threshold:
  configurable priority cutoffs (spec Step 16), same pattern as the
  existing bill_alert_days company setting.

Revision ID: 043_lead_intelligence_schema
Revises: 042_grant_production_delete
"""
from alembic import op

revision = "043_lead_intelligence_schema"
down_revision = "042_grant_production_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_leads ADD COLUMN source_lead_id VARCHAR(200) NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN received_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN raw_source_data JSONB NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN normalized_data JSONB NULL")

    op.execute("ALTER TABLE crm_leads ADD COLUMN score SMALLINT NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN priority VARCHAR(10) NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN score_version SMALLINT NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN score_breakdown JSONB NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN scored_at TIMESTAMPTZ NULL")

    op.execute("ALTER TABLE crm_leads ADD COLUMN duplicate_status VARCHAR(20) NOT NULL DEFAULT 'none'")
    op.execute("ALTER TABLE crm_leads ADD COLUMN duplicate_of_lead_id UUID NULL REFERENCES crm_leads(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN is_repeat_contact BOOLEAN NOT NULL DEFAULT FALSE")

    op.execute("CREATE INDEX idx_crm_leads_priority ON crm_leads (company_id, priority) WHERE priority IS NOT NULL")
    op.execute("CREATE INDEX idx_crm_leads_duplicate_of ON crm_leads (duplicate_of_lead_id) WHERE duplicate_of_lead_id IS NOT NULL")

    op.execute("ALTER TABLE companies ADD COLUMN lead_score_high_threshold SMALLINT NOT NULL DEFAULT 80")
    op.execute("ALTER TABLE companies ADD COLUMN lead_score_medium_threshold SMALLINT NOT NULL DEFAULT 50")


def downgrade() -> None:
    op.execute("ALTER TABLE companies DROP COLUMN lead_score_medium_threshold")
    op.execute("ALTER TABLE companies DROP COLUMN lead_score_high_threshold")
    op.execute("DROP INDEX idx_crm_leads_duplicate_of")
    op.execute("DROP INDEX idx_crm_leads_priority")
    op.execute("ALTER TABLE crm_leads DROP COLUMN is_repeat_contact")
    op.execute("ALTER TABLE crm_leads DROP COLUMN duplicate_of_lead_id")
    op.execute("ALTER TABLE crm_leads DROP COLUMN duplicate_status")
    op.execute("ALTER TABLE crm_leads DROP COLUMN scored_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN score_breakdown")
    op.execute("ALTER TABLE crm_leads DROP COLUMN score_version")
    op.execute("ALTER TABLE crm_leads DROP COLUMN priority")
    op.execute("ALTER TABLE crm_leads DROP COLUMN score")
    op.execute("ALTER TABLE crm_leads DROP COLUMN normalized_data")
    op.execute("ALTER TABLE crm_leads DROP COLUMN raw_source_data")
    op.execute("ALTER TABLE crm_leads DROP COLUMN received_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN source_lead_id")
