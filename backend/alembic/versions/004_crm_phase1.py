"""CRM Phase 1 — Leads, Pipeline, Persons, Organizations, Activities, Tags, WhatsApp

Revision ID: 004_crm_phase1
Revises: 003_materials_tables
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "004_crm_phase1"
down_revision = "003_materials_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── CRM Organizations ─────────────────────────────────────────────────────
    op.create_table(
        "crm_organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("website", sa.String(500)),
        sa.Column("address", JSONB),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_orgs_company", "crm_organizations", ["company_id"])

    # ── CRM Persons ───────────────────────────────────────────────────────────
    op.create_table(
        "crm_persons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("job_title", sa.String(200)),
        sa.Column("emails", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("contact_numbers", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("whatsapp_number", sa.String(50)),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("crm_organizations.id", ondelete="SET NULL")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_persons_company", "crm_persons", ["company_id"])
    op.create_index("ix_crm_persons_org", "crm_persons", ["organization_id"])

    # ── CRM Pipelines ─────────────────────────────────────────────────────────
    op.create_table(
        "crm_pipelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_default", sa.Boolean, default=False, nullable=False),
        sa.Column("rotten_days", sa.Integer, default=30),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── CRM Pipeline Stages ───────────────────────────────────────────────────
    op.create_table(
        "crm_pipeline_stages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(100)),
        sa.Column("probability", sa.Integer, default=0),   # 0–100
        sa.Column("sort_order", sa.Integer, default=0),
        sa.Column("is_won", sa.Boolean, default=False, nullable=False),
        sa.Column("is_lost", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_stages_pipeline", "crm_pipeline_stages", ["pipeline_id"])

    # ── CRM Lead Sources & Types ───────────────────────────────────────────────
    op.create_table(
        "crm_lead_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "crm_lead_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── CRM Leads ─────────────────────────────────────────────────────────────
    op.create_table(
        "crm_leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("lead_value", sa.Numeric(14, 4), default=0),
        sa.Column("status", sa.String(20), default="open", nullable=False),  # open / won / lost
        sa.Column("lost_reason", sa.Text),
        sa.Column("expected_close_date", sa.Date),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("rotten_at", sa.DateTime(timezone=True)),
        sa.Column("pipeline_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipelines.id", ondelete="SET NULL")),
        sa.Column("stage_id", UUID(as_uuid=True), sa.ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL")),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("crm_lead_sources.id", ondelete="SET NULL")),
        sa.Column("type_id", UUID(as_uuid=True), sa.ForeignKey("crm_lead_types.id", ondelete="SET NULL")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("crm_organizations.id", ondelete="SET NULL")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_leads_company", "crm_leads", ["company_id"])
    op.create_index("ix_crm_leads_stage", "crm_leads", ["stage_id"])
    op.create_index("ix_crm_leads_status", "crm_leads", ["status"])

    # ── CRM Tags ─────────────────────────────────────────────────────────────
    op.create_table(
        "crm_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), default="#6366F1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_crm_tags_company_name"),
    )

    op.create_table(
        "crm_lead_tags",
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", UUID(as_uuid=True), sa.ForeignKey("crm_tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "crm_person_tags",
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", UUID(as_uuid=True), sa.ForeignKey("crm_tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── CRM Activities ────────────────────────────────────────────────────────
    op.create_table(
        "crm_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),  # call/meeting/note/task/email/lunch
        sa.Column("comment", sa.Text),
        sa.Column("location", sa.String(300)),
        sa.Column("is_done", sa.Boolean, default=False, nullable=False),
        sa.Column("schedule_from", sa.DateTime(timezone=True)),
        sa.Column("schedule_to", sa.DateTime(timezone=True)),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="SET NULL")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_activities_lead", "crm_activities", ["lead_id"])
    op.create_index("ix_crm_activities_person", "crm_activities", ["person_id"])

    op.create_table(
        "crm_activity_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("activity_id", UUID(as_uuid=True), sa.ForeignKey("crm_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("path", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "crm_activity_participants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("activity_id", UUID(as_uuid=True), sa.ForeignKey("crm_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="CASCADE")),
    )

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    op.create_table(
        "whatsapp_contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(300)),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("company_id", "phone_number", name="uq_wa_contacts_company_phone"),
    )

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wa_message_id", sa.String(200)),
        sa.Column("direction", sa.String(10), nullable=False),     # inbound / outbound
        sa.Column("from_number", sa.String(50), nullable=False),
        sa.Column("to_number", sa.String(50), nullable=False),
        sa.Column("message_type", sa.String(50), default="text"), # text/image/document/template
        sa.Column("body", sa.Text),
        sa.Column("media_url", sa.String(1000)),
        sa.Column("media_mime_type", sa.String(200)),
        sa.Column("status", sa.String(30), default="sent"),        # sent/delivered/read/failed
        sa.Column("wa_timestamp", sa.DateTime(timezone=True)),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("whatsapp_contacts.id", ondelete="SET NULL")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_wa_messages_contact", "whatsapp_messages", ["contact_id"])
    op.create_index("ix_wa_messages_lead", "whatsapp_messages", ["lead_id"])

    op.create_table(
        "whatsapp_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("language", sa.String(20), default="en"),
        sa.Column("category", sa.String(50)),                     # MARKETING/UTILITY/AUTHENTICATION
        sa.Column("body_text", sa.Text),                          # template body with {{variables}}
        sa.Column("components", JSONB),                           # full Meta API components
        sa.Column("wa_template_id", sa.String(200)),
        sa.Column("status", sa.String(30), default="pending"),    # pending/approved/rejected
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── Seed default pipeline and lead sources ────────────────────────────────
    op.execute("""
        INSERT INTO crm_pipelines (id, company_id, name, is_default, rotten_days)
        SELECT gen_random_uuid(), c.id, 'Sales Pipeline', true, 30
        FROM companies c
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        WITH pipeline AS (
            SELECT p.id AS pid, c.id AS cid
            FROM crm_pipelines p
            JOIN companies c ON p.company_id = c.id
            WHERE p.is_default = true
            LIMIT 1
        )
        INSERT INTO crm_pipeline_stages (id, pipeline_id, name, code, probability, sort_order, is_won, is_lost)
        SELECT gen_random_uuid(), pid, name, code, prob, ord, is_won, is_lost
        FROM pipeline
        CROSS JOIN (VALUES
            ('New',          'new',          20,  1,  false, false),
            ('Qualified',    'qualified',    40,  2,  false, false),
            ('Proposal',     'proposal',     60,  3,  false, false),
            ('Negotiation',  'negotiation',  80,  4,  false, false),
            ('Won',          'won',          100, 5,  true,  false),
            ('Lost',         'lost',         0,   6,  false, true)
        ) AS s(name, code, prob, ord, is_won, is_lost)
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO crm_lead_sources (id, company_id, name)
        SELECT gen_random_uuid(), c.id, src
        FROM companies c
        CROSS JOIN (VALUES ('Website'),('Cold Call'),('Email'),('Referral'),('Social Media'),('Trade Show'),('Other')) AS s(src)
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO crm_lead_types (id, company_id, name)
        SELECT gen_random_uuid(), c.id, t
        FROM companies c
        CROSS JOIN (VALUES ('New Business'),('Existing Business'),('Upsell'),('Renewal')) AS t(t)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS whatsapp_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS whatsapp_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS whatsapp_contacts CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_activity_participants CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_activity_files CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_activities CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_person_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_lead_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_leads CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_lead_types CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_lead_sources CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_pipeline_stages CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_pipelines CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_persons CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_organizations CASCADE")
