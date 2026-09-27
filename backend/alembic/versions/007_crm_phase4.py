"""CRM Phase 4 — Email templates, lead import log

Revision ID: 007_crm_phase4
Revises: 006_crm_phase3
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007_crm_phase4"
down_revision = "006_crm_phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── CRM Email Templates ───────────────────────────────────────────────────
    op.create_table(
        "crm_email_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("subject", sa.String(1000), nullable=False),
        sa.Column("body_text", sa.Text, nullable=False),
        sa.Column("body_html", sa.Text),
        sa.Column("category", sa.String(100)),             # intro / follow-up / quote / closing
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_email_templates_company", "crm_email_templates", ["company_id"])

    # ── CRM Lead Import Batches ───────────────────────────────────────────────
    op.create_table(
        "crm_lead_imports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("total_rows", sa.Integer, default=0),
        sa.Column("imported_rows", sa.Integer, default=0),
        sa.Column("failed_rows", sa.Integer, default=0),
        sa.Column("status", sa.String(30), default="pending"),   # pending/processing/done/failed
        sa.Column("errors", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pipeline_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipelines.id", ondelete="SET NULL")),
        sa.Column("stage_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL")),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_crm_lead_imports_company", "crm_lead_imports", ["company_id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_lead_imports CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_email_templates CASCADE")
