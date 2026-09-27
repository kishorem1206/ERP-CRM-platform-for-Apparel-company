"""CRM Phase 3 — Email threads, lead→SO link, rotten lead tracking

Revision ID: 006_crm_phase3
Revises: 005_crm_phase2
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT

revision = "006_crm_phase3"
down_revision = "005_crm_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Add sales_order_id to crm_leads (lead→SO conversion link) ────────────
    op.add_column(
        "crm_leads",
        sa.Column("sales_order_id", UUID(as_uuid=True),
                  sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True),
    )

    # ── CRM Emails ────────────────────────────────────────────────────────────
    op.create_table(
        "crm_emails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),        # outbound / inbound
        sa.Column("subject", sa.String(1000), nullable=False),
        sa.Column("body_html", sa.Text),
        sa.Column("body_text", sa.Text),
        sa.Column("from_address", sa.String(500), nullable=False),
        sa.Column("to_addresses", ARRAY(TEXT), server_default=sa.text("'{}'")),
        sa.Column("cc_addresses", ARRAY(TEXT), server_default=sa.text("'{}'")),
        sa.Column("bcc_addresses", ARRAY(TEXT), server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(20), default="draft"),          # draft/sent/failed/received
        sa.Column("error_message", sa.Text),
        sa.Column("message_id", sa.String(500)),                      # SMTP Message-ID header
        sa.Column("in_reply_to", sa.String(500)),                     # for threading
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="SET NULL")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("crm_quotes.id", ondelete="SET NULL")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_emails_lead", "crm_emails", ["lead_id"])
    op.create_index("ix_crm_emails_person", "crm_emails", ["person_id"])
    op.create_index("ix_crm_emails_company", "crm_emails", ["company_id"])

    # ── CRM Email Attachments ─────────────────────────────────────────────────
    op.create_table(
        "crm_email_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email_id", UUID(as_uuid=True), sa.ForeignKey("crm_emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(200)),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    # ── SMTP Config (per company) ──────────────────────────────────────────────
    op.create_table(
        "crm_smtp_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False, unique=True),
        sa.Column("host", sa.String(300), nullable=False),
        sa.Column("port", sa.Integer, default=587),
        sa.Column("username", sa.String(300), nullable=False),
        sa.Column("password_encrypted", sa.String(1000), nullable=False),  # AES-encrypted
        sa.Column("from_name", sa.String(300)),
        sa.Column("from_email", sa.String(300), nullable=False),
        sa.Column("use_tls", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_smtp_configs CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_email_attachments CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_emails CASCADE")
    op.execute("DROP COLUMN IF EXISTS crm_leads.sales_order_id")
    op.drop_column("crm_leads", "sales_order_id")
