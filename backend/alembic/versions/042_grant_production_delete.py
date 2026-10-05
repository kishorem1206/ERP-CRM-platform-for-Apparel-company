"""Grant production.delete to Administrator (used by size-chart delete since Upgrade #2 Phase 3).

Revision ID: 042_grant_production_delete
Revises: 041_bill_alert_days
"""
from alembic import op

revision = "042_grant_production_delete"
down_revision = "041_bill_alert_days"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'production.delete') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Administrator' AND p.code = 'production.delete'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'production.delete')")
    op.execute("DELETE FROM permissions WHERE code = 'production.delete'")
