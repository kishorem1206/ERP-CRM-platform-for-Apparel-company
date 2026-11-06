"""PO receipt tolerance and closing.

Each PO line gets a tolerance (± % of the ordered quantity) set when the PO
is raised. A PO received within every line's range can be closed by whoever
raised it; one received short or over needs an admin (the new
purchase.po_close_approve permission) to approve the close. The tolerance
and the approval trail are internal only — they never appear on the PDFs.

Revision ID: 069_po_tolerance_close
Revises: 068_trim_types_balance
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "069_po_tolerance_close"
down_revision = "068_trim_types_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order_items", sa.Column("tolerance_pct", sa.Numeric(5, 2)))
    op.add_column("purchase_orders", sa.Column("close_reason", sa.Text()))
    op.add_column("purchase_orders", sa.Column("close_requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id")))
    op.add_column("purchase_orders", sa.Column("close_requested_at", sa.DateTime(timezone=True)))
    op.add_column("purchase_orders", sa.Column("closed_by", UUID(as_uuid=True), sa.ForeignKey("users.id")))
    op.add_column("purchase_orders", sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'purchase.po_close_approve') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Administrator' AND p.code = 'purchase.po_close_approve'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'purchase.po_close_approve')")
    op.execute("DELETE FROM permissions WHERE code = 'purchase.po_close_approve'")
    for col in ("closed_at", "closed_by", "close_requested_at", "close_requested_by", "close_reason"):
        op.drop_column("purchase_orders", col)
    op.drop_column("purchase_order_items", "tolerance_pct")
