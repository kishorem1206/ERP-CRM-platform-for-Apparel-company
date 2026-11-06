"""Retail Sales, stage 1: retail customers, estimates, invoices, payments
and discount settings — kept apart from the B2B sales tables.

Permissions (granted to the Administrator role; give the others from
Roles & Permissions):
  retail.view             see retail screens
  retail.create           bills, estimates, register customers
  retail.collect          record payments against credit bills
  retail.manage           retail settings, cancel bills
  retail.discount_approve bill above the maximum discount

Revision ID: 074_retail_core
Revises: 073_tds_part_weights
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "074_retail_core"
down_revision = "073_tds_part_weights"
branch_labels = None
depends_on = None

PERMS = ("retail.view", "retail.create", "retail.collect", "retail.manage", "retail.discount_approve")


def _uuid_pk():
    return sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _fk(name, target, nullable=True, ondelete=None):
    return sa.Column(name, UUID(as_uuid=True), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _money(name, nullable=True, default="0"):
    return sa.Column(name, sa.Numeric(15, 2), nullable=nullable, server_default=default)


def _line_columns():
    return [
        _fk("product_id", "products.id", nullable=False),
        _fk("variant_id", "product_variants.id"),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("hsn_code", sa.String(8)),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("gross_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("item_discount_pct", sa.Numeric(5, 2), server_default="0"),
        _money("discount_amount"),
        sa.Column("gst_rate", sa.Numeric(5, 2), server_default="0"),
        sa.Column("taxable_amount", sa.Numeric(15, 2), nullable=False),
        _money("cgst_amount"),
        _money("sgst_amount"),
        sa.Column("net_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    ]


def _totals_columns():
    return [
        sa.Column("bill_discount_pct", sa.Numeric(5, 2), server_default="0"),
        _money("gross_amount"), _money("discount_amount"), _money("taxable_amount"),
        _money("cgst_amount"), _money("sgst_amount"),
        sa.Column("round_off", sa.Numeric(6, 2), server_default="0"),
        _money("total_amount"),
        _fk("discount_approved_by", "users.id"),
        sa.Column("notes", sa.Text),
    ]


def upgrade() -> None:
    op.create_table(
        "retail_settings",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("min_discount_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("max_discount_pct", sa.Numeric(5, 2), server_default="10"),
        sa.Column("default_discount_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("allow_approved_override", sa.Boolean, server_default=sa.true()),
        _fk("warehouse_id", "warehouses.id"),
        sa.Column("credit_days", sa.Integer, server_default="30"),
        sa.Column("estimate_validity_days", sa.Integer, server_default="7"),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        _fk("updated_by", "users.id"),
    )
    op.create_table(
        "retail_settings_audit",
        _uuid_pk(),
        _fk("company_id", "companies.id", nullable=False),
        sa.Column("field", sa.String(60), nullable=False),
        sa.Column("old_value", sa.String(200)),
        sa.Column("new_value", sa.String(200)),
        _fk("changed_by", "users.id"),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "retail_customers",
        _uuid_pk(),
        _fk("company_id", "companies.id", nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mobile", sa.String(15), nullable=False),
        sa.Column("email", sa.String(150)),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("gender", sa.String(20)),
        sa.Column("billing_address", sa.Text),
        sa.Column("shipping_address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("pincode", sa.String(10)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _fk("created_by", "users.id"),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("company_id", "mobile", name="uq_retail_customers_mobile"),
    )
    op.create_index("ix_retail_customers_company_name", "retail_customers", ["company_id", "name"])

    op.create_table(
        "retail_estimates",
        _uuid_pk(),
        _fk("company_id", "companies.id", nullable=False),
        sa.Column("estimate_number", sa.String(30), nullable=False),
        _fk("customer_id", "retail_customers.id"),
        sa.Column("estimate_date", sa.Date, nullable=False),
        sa.Column("valid_until", sa.Date),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("converted_invoice_id", UUID(as_uuid=True)),   # FK added below, after retail_invoices
        _fk("created_by", "users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        *_totals_columns(),
        sa.UniqueConstraint("company_id", "estimate_number", name="uq_retail_estimates_number"),
    )
    op.create_table(
        "retail_estimate_items",
        _uuid_pk(),
        _fk("estimate_id", "retail_estimates.id", nullable=False, ondelete="CASCADE"),
        *_line_columns(),
    )
    op.create_table(
        "retail_invoices",
        _uuid_pk(),
        _fk("company_id", "companies.id", nullable=False),
        sa.Column("invoice_number", sa.String(30), nullable=False),
        sa.Column("client_ref", sa.String(64)),
        _fk("customer_id", "retail_customers.id"),
        sa.Column("invoice_date", sa.Date, nullable=False),
        _fk("warehouse_id", "warehouses.id", nullable=False),
        sa.Column("payment_mode", sa.String(10), nullable=False),
        sa.Column("payment_status", sa.String(20), nullable=False),
        _money("amount_paid"),
        sa.Column("due_date", sa.Date),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        _fk("estimate_id", "retail_estimates.id"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        _fk("cancelled_by", "users.id"),
        sa.Column("cancel_reason", sa.Text),
        _fk("created_by", "users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_totals_columns(),
        sa.UniqueConstraint("company_id", "invoice_number", name="uq_retail_invoices_number"),
        sa.UniqueConstraint("company_id", "client_ref", name="uq_retail_invoices_client_ref"),
    )
    op.create_index("ix_retail_invoices_company_date", "retail_invoices", ["company_id", "invoice_date"])
    op.create_index("ix_retail_invoices_customer", "retail_invoices", ["customer_id"])
    op.create_foreign_key(
        "fk_retail_estimates_converted_invoice", "retail_estimates", "retail_invoices",
        ["converted_invoice_id"], ["id"],
    )
    op.create_table(
        "retail_invoice_items",
        _uuid_pk(),
        _fk("invoice_id", "retail_invoices.id", nullable=False, ondelete="CASCADE"),
        *_line_columns(),
        _fk("unit_id", "units.id"),
        sa.Column("unit_cost", sa.Numeric(15, 4), server_default="0"),
        _fk("inv_transaction_id", "inventory_transactions.id"),
    )
    op.create_table(
        "retail_payments",
        _uuid_pk(),
        _fk("company_id", "companies.id", nullable=False),
        _fk("invoice_id", "retail_invoices.id", nullable=False),
        sa.Column("receipt_number", sa.String(30), nullable=False),
        sa.Column("client_ref", sa.String(64)),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="cash"),
        sa.Column("reference", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        _fk("created_by", "users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "receipt_number", name="uq_retail_payments_receipt"),
        sa.UniqueConstraint("company_id", "client_ref", name="uq_retail_payments_client_ref"),
    )
    op.create_index("ix_retail_payments_invoice", "retail_payments", ["invoice_id"])

    for code in PERMS:
        op.execute(f"INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), '{code}') ON CONFLICT DO NOTHING")
    op.execute(f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Administrator' AND p.code IN {PERMS}
        ON CONFLICT DO NOTHING
    """)
    # Counter sales come out of the finished-goods store by default.
    op.execute("""
        INSERT INTO retail_settings (company_id, warehouse_id, updated_at)
        SELECT c.id, (
            SELECT w.id FROM warehouses w
            WHERE w.company_id = c.id
            ORDER BY (w.material_type = 'finished_good') DESC NULLS LAST, (w.code = 'WH-FG') DESC, w.name
            LIMIT 1
        ), now()
        FROM companies c
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(f"DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN {PERMS})")
    op.execute(f"DELETE FROM permissions WHERE code IN {PERMS}")
    op.drop_table("retail_payments")
    op.drop_table("retail_invoice_items")
    op.drop_constraint("fk_retail_estimates_converted_invoice", "retail_estimates", type_="foreignkey")
    op.drop_table("retail_invoices")
    op.drop_table("retail_estimate_items")
    op.drop_table("retail_estimates")
    op.drop_table("retail_customers")
    op.drop_table("retail_settings_audit")
    op.drop_table("retail_settings")
