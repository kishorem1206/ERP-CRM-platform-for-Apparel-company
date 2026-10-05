"""ERP Upgrade Phase 7: Product Merge.

- products gains merged_into_id (self-referential, nullable) - traces a
  merged-away product to what it became, alongside the existing (now
  finally used) is_active/deleted_at soft-delete fields.
- new product_merge_logs table: narrow, merge-specific audit trail (not
  the larger generic audit_logs design docs/PRODUCT.md describes for
  every entity type - that's a separate, much larger, unrequested effort).
- new master_data.merge permission, auto-granted to roles already
  holding master_data.delete - same pattern as crm.assign (020).

Revision ID: 032_product_merge
Revises: 031_stock_adjustment_unify
"""
from alembic import op

revision = "032_product_merge"
down_revision = "031_stock_adjustment_unify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS merged_into_id UUID REFERENCES products(id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS product_merge_logs (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id         UUID NOT NULL REFERENCES companies(id),
            source_product_id UUID NOT NULL REFERENCES products(id),
            source_code        VARCHAR(50) NOT NULL,
            source_name        VARCHAR(300) NOT NULL,
            target_product_id  UUID NOT NULL REFERENCES products(id),
            target_code        VARCHAR(50) NOT NULL,
            target_name        VARCHAR(300) NOT NULL,
            notes              TEXT,
            merged_by          UUID REFERENCES users(id) ON DELETE SET NULL,
            merged_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_merge_logs_company ON product_merge_logs(company_id)")

    op.execute("INSERT INTO permissions (id, code) VALUES (gen_random_uuid(), 'master_data.merge') ON CONFLICT DO NOTHING")
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT rp.role_id, p.id
        FROM role_permissions rp
        JOIN permissions ep ON ep.id = rp.permission_id AND ep.code = 'master_data.delete'
        CROSS JOIN permissions p
        WHERE p.code = 'master_data.merge'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'master_data.merge')")
    op.execute("DELETE FROM permissions WHERE code = 'master_data.merge'")
    op.execute("DROP TABLE IF EXISTS product_merge_logs")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS merged_into_id")
