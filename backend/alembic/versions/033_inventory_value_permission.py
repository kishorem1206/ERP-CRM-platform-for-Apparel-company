"""ERP Upgrade Phase 8 (final): Stock Value admin-only visibility.

- new inventory.value permission, granted directly to the role named
  'Administrator' in every company - seed.py identifies the admin role
  the same way, but seeding is one-time and won't retroactively apply to
  an already-seeded database, so this has to be a real migration grant.

Revision ID: 033_inventory_value_permission
Revises: 032_product_merge
"""
from alembic import op

revision = "033_inventory_value_permission"
down_revision = "032_product_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'inventory.value') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Administrator' AND p.code = 'inventory.value'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'inventory.value')")
    op.execute("DELETE FROM permissions WHERE code = 'inventory.value'")
