"""CRM sales KPIs: configurable qualification stage per pipeline.

The KPI "Lead -> Qualified" needs to know which stage of a pipeline means
"qualified". Stored once per pipeline so reporting never hardcodes a stage
name. The backfill below is one-time, for the pipelines the original seed
created (whose stage is named "Qualified"); after it runs, the stage used
for reporting is only whatever crm_pipelines.qualified_stage_id points to.

Revision ID: 047_pipeline_qualification_stage
Revises: 046_predictive_scoring_readiness
"""
from alembic import op

revision = "047_pipeline_qualification_stage"
down_revision = "046_predictive_scoring_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE crm_pipelines ADD COLUMN qualified_stage_id UUID "
        "REFERENCES crm_pipeline_stages(id) ON DELETE SET NULL"
    )
    op.execute(
        """
        UPDATE crm_pipelines p
        SET qualified_stage_id = (
            SELECT s.id FROM crm_pipeline_stages s
            WHERE s.pipeline_id = p.id AND lower(s.name) = 'qualified'
            ORDER BY s.sort_order
            LIMIT 1
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE crm_pipelines DROP COLUMN qualified_stage_id")
