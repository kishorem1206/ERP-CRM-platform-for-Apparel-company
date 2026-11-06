"""Retail Sales, stage 3: credit collections, receipts, payment cancellation
and partial returns.

- retail_payments.batch_ref groups the payments of one collection (a
  customer paying against several bills) so they print on one receipt;
  payments can be cancelled with a reason (kept, never deleted).
- retail_returns / retail_return_items: items handed back from a bill.
  Stock goes back at the cost it left at; the value first reduces what the
  customer still owes on that bill, anything beyond is refunded.
- retail_invoices: returned_amount, refunded_amount, points_returned. A
  bill's outstanding = total - returned - (paid - refunded).

Revision ID: 076_retail_credit_returns
Revises: 075_retail_engagement
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "076_retail_credit_returns"
down_revision = "075_retail_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("retail_payments", sa.Column("batch_ref", UUID(as_uuid=True)))
    op.add_column("retail_payments", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column("retail_payments", sa.Column("cancelled_by", UUID(as_uuid=True), sa.ForeignKey("users.id")))
    op.add_column("retail_payments", sa.Column("cancel_reason", sa.Text))
    op.execute("UPDATE retail_payments SET batch_ref = id WHERE batch_ref IS NULL")
    # One receipt number per collection: the payments of a batch share it.
    op.drop_constraint("uq_retail_payments_receipt", "retail_payments", type_="unique")
    op.create_index("ix_retail_payments_receipt", "retail_payments", ["company_id", "receipt_number"])
    op.create_index("ix_retail_payments_batch", "retail_payments", ["batch_ref"])
    op.create_index("ix_retail_payments_company_date", "retail_payments", ["company_id", "payment_date"])

    for col in ("returned_amount", "refunded_amount"):
        op.add_column("retail_invoices", sa.Column(col, sa.Numeric(15, 2), server_default="0", nullable=False))
    op.add_column("retail_invoices", sa.Column("points_returned", sa.Integer, server_default="0", nullable=False))
    op.create_index("ix_retail_invoices_due", "retail_invoices", ["company_id", "payment_mode", "due_date"])

    op.create_table(
        "retail_returns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("return_number", sa.String(30), nullable=False),
        sa.Column("client_ref", sa.String(64)),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("retail_invoices.id"), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("retail_customers.id")),
        sa.Column("return_date", sa.Date, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("return_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("taxable_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("applied_to_balance", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("refund_amount", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("refund_mode", sa.String(20)),
        sa.Column("points_reversed", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "return_number", name="uq_retail_returns_number"),
        sa.UniqueConstraint("company_id", "client_ref", name="uq_retail_returns_client_ref"),
    )
    op.create_index("ix_retail_returns_invoice", "retail_returns", ["invoice_id"])
    op.create_table(
        "retail_return_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("return_id", UUID(as_uuid=True), sa.ForeignKey("retail_returns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_item_id", UUID(as_uuid=True), sa.ForeignKey("retail_invoice_items.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("product_variants.id")),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("taxable_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(15, 4), server_default="0", nullable=False),
        sa.Column("inv_transaction_id", UUID(as_uuid=True), sa.ForeignKey("inventory_transactions.id")),
    )


def downgrade() -> None:
    op.drop_table("retail_return_items")
    op.drop_index("ix_retail_returns_invoice", table_name="retail_returns")
    op.drop_table("retail_returns")
    op.drop_index("ix_retail_invoices_due", table_name="retail_invoices")
    for col in ("points_returned", "refunded_amount", "returned_amount"):
        op.drop_column("retail_invoices", col)
    op.drop_index("ix_retail_payments_receipt", table_name="retail_payments")
    op.create_unique_constraint("uq_retail_payments_receipt", "retail_payments", ["company_id", "receipt_number"])
    op.drop_index("ix_retail_payments_company_date", table_name="retail_payments")
    op.drop_index("ix_retail_payments_batch", table_name="retail_payments")
    for col in ("cancel_reason", "cancelled_by", "cancelled_at", "batch_ref"):
        op.drop_column("retail_payments", col)
