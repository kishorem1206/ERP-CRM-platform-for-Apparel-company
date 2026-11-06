"""Vendor contacts/bank details editable in full, and user-added vendor types.

Contacts get a designation and notes; bank accounts a branch and notes.
vendor_types holds the types a company adds (e.g. "Embroiderer") on top of
the four built in to the app (supplier, job worker, transporter, agent).

Revision ID: 070_vendor_contacts_types
Revises: 069_po_tolerance_close
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "070_vendor_contacts_types"
down_revision = "069_po_tolerance_close"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendor_contacts", sa.Column("designation", sa.String(100)))
    op.add_column("vendor_contacts", sa.Column("notes", sa.Text()))
    op.add_column("vendor_bank_details", sa.Column("branch", sa.String(100)))
    op.add_column("vendor_bank_details", sa.Column("notes", sa.Text()))
    op.create_table(
        "vendor_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("company_id", "code", name="uq_vendor_types_company_code"),
    )


def downgrade() -> None:
    op.drop_table("vendor_types")
    op.drop_column("vendor_bank_details", "notes")
    op.drop_column("vendor_bank_details", "branch")
    op.drop_column("vendor_contacts", "notes")
    op.drop_column("vendor_contacts", "designation")
