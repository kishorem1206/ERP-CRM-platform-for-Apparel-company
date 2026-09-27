"""CRM Phase 5 — Lead temperature, person city, stage color, stage history, notes

Revision ID: 008_crm_phase5
Revises: 007_crm_phase4
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008_crm_phase5"
down_revision = "007_crm_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Lead: temperature field ────────────────────────────────────────────────
    op.add_column(
        "crm_leads",
        sa.Column("temperature", sa.String(10), nullable=False, server_default="cold"),
    )

    # ── Person: city field ────────────────────────────────────────────────────
    op.add_column(
        "crm_persons",
        sa.Column("city", sa.String(200), nullable=True),
    )

    # ── Pipeline stage: color field ───────────────────────────────────────────
    op.add_column(
        "crm_pipeline_stages",
        sa.Column("color", sa.String(20), nullable=True, server_default="#6366f1"),
    )

    # ── Stage history ─────────────────────────────────────────────────────────
    op.create_table(
        "crm_lead_stage_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_stage_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_stage_name", sa.String(200)),
        sa.Column("to_stage_name", sa.String(200)),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("changed_by_name", sa.String(300)),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_stage_history_lead", "crm_lead_stage_history", ["lead_id"])
    op.create_index("ix_crm_stage_history_changed_at", "crm_lead_stage_history", ["changed_at"])

    # ── Notes ─────────────────────────────────────────────────────────────────
    op.create_table(
        "crm_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="CASCADE"), nullable=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("crm_organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_name", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_notes_company", "crm_notes", ["company_id"])
    op.create_index("ix_crm_notes_person", "crm_notes", ["person_id"])
    op.create_index("ix_crm_notes_lead", "crm_notes", ["lead_id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_notes CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_lead_stage_history CASCADE")
    op.drop_column("crm_pipeline_stages", "color")
    op.drop_column("crm_persons", "city")
    op.drop_column("crm_leads", "temperature")
