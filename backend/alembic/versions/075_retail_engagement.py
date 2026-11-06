"""Retail Sales, stage 2: coupons, loyalty points and birthday offers.

- retail_coupons / retail_coupon_redemptions: manual, promotional and
  birthday coupons with usage limits and redemption history.
- retail_loyalty_ledger: every point earned, redeemed, expired, adjusted or
  reversed, with the balance after it. retail_customers.loyalty_points
  caches the balance.
- retail_settings gains the loyalty and birthday-offer rules.
- retail_invoices record the coupon, points used and points earned.

Revision ID: 075_retail_engagement
Revises: 074_retail_core
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "075_retail_engagement"
down_revision = "074_retail_core"
branch_labels = None
depends_on = None

SETTINGS_COLS = [
    sa.Column("loyalty_enabled", sa.Boolean, server_default=sa.false(), nullable=False),
    sa.Column("amount_per_point", sa.Numeric(10, 2), server_default="100", nullable=False),
    sa.Column("min_bill_for_points", sa.Numeric(12, 2), server_default="0", nullable=False),
    sa.Column("min_redeem_points", sa.Integer, server_default="100", nullable=False),
    sa.Column("point_value", sa.Numeric(8, 2), server_default="1", nullable=False),
    sa.Column("max_redeem_pct", sa.Numeric(5, 2), server_default="20", nullable=False),
    sa.Column("points_expiry_days", sa.Integer, server_default="365", nullable=False),
    sa.Column("loyalty_excluded_category_ids", ARRAY(UUID(as_uuid=True)), server_default="{}", nullable=False),
    sa.Column("birthday_enabled", sa.Boolean, server_default=sa.false(), nullable=False),
    sa.Column("birthday_discount_type", sa.String(10), server_default="percent", nullable=False),
    sa.Column("birthday_discount_value", sa.Numeric(12, 2), server_default="10", nullable=False),
    sa.Column("birthday_min_purchase", sa.Numeric(12, 2), server_default="0", nullable=False),
    sa.Column("birthday_max_discount", sa.Numeric(12, 2)),
    sa.Column("birthday_window", sa.String(10), server_default="week", nullable=False),
    sa.Column("birthday_lead_days", sa.Integer, server_default="7", nullable=False),
]


def upgrade() -> None:
    for col in SETTINGS_COLS:
        op.add_column("retail_settings", col)
    op.add_column("retail_customers", sa.Column("loyalty_points", sa.Integer, server_default="0", nullable=False))

    op.create_table(
        "retail_coupons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("kind", sa.String(20), nullable=False, server_default="manual"),       # manual / promo / birthday
        sa.Column("discount_type", sa.String(10), nullable=False),                         # percent / fixed
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("min_purchase", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("max_discount", sa.Numeric(12, 2)),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("max_uses", sa.Integer),
        sa.Column("per_customer_limit", sa.Integer),
        sa.Column("product_ids", ARRAY(UUID(as_uuid=True)), server_default="{}", nullable=False),
        sa.Column("category_ids", ARRAY(UUID(as_uuid=True)), server_default="{}", nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("retail_customers.id")),  # only this customer
        sa.Column("birthday_year", sa.Integer),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("company_id", "code", name="uq_retail_coupons_code"),
    )
    op.create_index(
        "uq_retail_coupons_birthday", "retail_coupons", ["customer_id", "birthday_year"],
        unique=True, postgresql_where=sa.text("kind = 'birthday'"),
    )
    op.create_table(
        "retail_coupon_redemptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("coupon_id", UUID(as_uuid=True), sa.ForeignKey("retail_coupons.id"), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("retail_invoices.id"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("retail_customers.id")),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),     # active / reversed
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retail_coupon_redemptions_coupon", "retail_coupon_redemptions", ["coupon_id"])
    op.create_table(
        "retail_loyalty_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("retail_customers.id"), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),   # earned / redeemed / expired / adjusted / reversed
        sa.Column("points", sa.Integer, nullable=False),          # + adds to the balance, - takes away
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("retail_invoices.id")),
        sa.Column("reason", sa.Text),
        sa.Column("expires_on", sa.Date),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retail_loyalty_ledger_customer", "retail_loyalty_ledger", ["customer_id", "created_at"])

    op.add_column("retail_invoices", sa.Column("coupon_id", UUID(as_uuid=True), sa.ForeignKey("retail_coupons.id")))
    op.add_column("retail_invoices", sa.Column("coupon_discount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("retail_invoices", sa.Column("points_redeemed", sa.Integer, server_default="0", nullable=False))
    op.add_column("retail_invoices", sa.Column("points_discount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("retail_invoices", sa.Column("points_earned", sa.Integer, server_default="0", nullable=False))
    op.add_column("retail_invoices", sa.Column("points_awarded", sa.Boolean, server_default=sa.false(), nullable=False))


def downgrade() -> None:
    for col in ("points_awarded", "points_earned", "points_discount", "points_redeemed", "coupon_discount", "coupon_id"):
        op.drop_column("retail_invoices", col)
    op.drop_table("retail_loyalty_ledger")
    op.drop_table("retail_coupon_redemptions")
    op.drop_index("uq_retail_coupons_birthday", table_name="retail_coupons")
    op.drop_table("retail_coupons")
    op.drop_column("retail_customers", "loyalty_points")
    for col in reversed(SETTINGS_COLS):
        op.drop_column("retail_settings", col.name)
