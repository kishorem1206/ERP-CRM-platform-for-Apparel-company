"""purchase.grn_edit: correcting a saved GRN (quantities, rejects, prices).

Granted to the Administrator role only; other roles can be given it from
Roles & Permissions.

Revision ID: 066_grn_edit_permission
Revises: 065_lot_materials
"""
from alembic import op

revision = "066_grn_edit_permission"
down_revision = "065_lot_materials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'purchase.grn_edit') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Administrator' AND p.code = 'purchase.grn_edit'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'purchase.grn_edit')")
    op.execute("DELETE FROM permissions WHERE code = 'purchase.grn_edit'")
