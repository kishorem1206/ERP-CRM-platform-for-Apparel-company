"""CRM Phase 2 — Products, Quotes, Quote Items

Revision ID: 005_crm_phase2
Revises: 004_crm_phase1
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005_crm_phase2"
down_revision = "004_crm_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── CRM Products (catalog items for quoting — no stock) ───────────────────
    op.create_table(
        "crm_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("sku", sa.String(100)),
        sa.Column("price", sa.Numeric(14, 4), default=0),
        sa.Column("currency", sa.String(10), default="INR"),
        sa.Column("unit", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_crm_products_company", "crm_products", ["company_id"])

    # ── CRM Quotes ─────────────────────────────────────────────────────────────
    op.create_table(
        "crm_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("quote_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), default="draft", nullable=False),  # draft/sent/accepted/declined/expired
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("crm_leads.id", ondelete="SET NULL")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("crm_persons.id", ondelete="SET NULL")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("crm_organizations.id", ondelete="SET NULL")),
        sa.Column("valid_until", sa.Date),
        sa.Column("currency", sa.String(10), default="INR"),
        sa.Column("subtotal", sa.Numeric(14, 4), default=0),
        sa.Column("discount_percent", sa.Numeric(5, 2), default=0),
        sa.Column("discount_amount", sa.Numeric(14, 4), default=0),
        sa.Column("tax_amount", sa.Numeric(14, 4), default=0),
        sa.Column("total_amount", sa.Numeric(14, 4), default=0),
        sa.Column("notes", sa.Text),
        sa.Column("terms", sa.Text),
        sa.Column("sales_order_id", UUID(as_uuid=True), sa.ForeignKey("sales_orders.id", ondelete="SET NULL")),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("company_id", "quote_number", name="uq_crm_quotes_number"),
    )
    op.create_index("ix_crm_quotes_company", "crm_quotes", ["company_id"])
    op.create_index("ix_crm_quotes_lead", "crm_quotes", ["lead_id"])
    op.create_index("ix_crm_quotes_status", "crm_quotes", ["status"])

    # ── CRM Quote Items ────────────────────────────────────────────────────────
    op.create_table(
        "crm_quote_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("crm_quotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("crm_products.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(400), nullable=False),   # snapshot of product name
        sa.Column("description", sa.Text),
        sa.Column("quantity", sa.Numeric(10, 3), default=1),
        sa.Column("unit_price", sa.Numeric(14, 4), default=0),
        sa.Column("discount_percent", sa.Numeric(5, 2), default=0),
        sa.Column("total", sa.Numeric(14, 4), default=0),
        sa.Column("sort_order", sa.Integer, default=0),
    )
    op.create_index("ix_crm_quote_items_quote", "crm_quote_items", ["quote_id"])

    # ── Quote number sequence ──────────────────────────────────────────────────
    op.execute("CREATE SEQUENCE IF NOT EXISTS crm_quote_seq START 1001 INCREMENT 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS crm_quote_seq")
    op.execute("DROP TABLE IF EXISTS crm_quote_items CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_quotes CASCADE")
    op.execute("DROP TABLE IF EXISTS crm_products CASCADE")
