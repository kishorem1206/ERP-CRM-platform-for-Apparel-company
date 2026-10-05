"""Predictive Lead Scoring Phase 1: data-sufficiency gate only.

The data audit (docs/PREDICTIVE_SCORING_DATA_AUDIT.md) found 9 total leads
for the real company, 1 won, 1 lost - nowhere near enough to train
anything. Per the spec's own instruction ("do not fabricate model
accuracy... build the data foundation"), no model, feature store, or
training pipeline is being built. This migration adds only the
configurable thresholds the readiness check (GET
/crm/predictive-scoring/readiness) compares real counts against, so the
system can honestly report "not ready" with real numbers instead of
either staying silent or showing something fake.

Revision ID: 046_predictive_scoring_readiness
Revises: 045_lead_assignment_engine
"""
from alembic import op

revision = "046_predictive_scoring_readiness"
down_revision = "045_lead_assignment_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE companies ADD COLUMN predictive_scoring_min_leads SMALLINT NOT NULL DEFAULT 200")
    op.execute("ALTER TABLE companies ADD COLUMN predictive_scoring_min_outcomes_per_class SMALLINT NOT NULL DEFAULT 30")


def downgrade() -> None:
    op.execute("ALTER TABLE companies DROP COLUMN predictive_scoring_min_outcomes_per_class")
    op.execute("ALTER TABLE companies DROP COLUMN predictive_scoring_min_leads")
