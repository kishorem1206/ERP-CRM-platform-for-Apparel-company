"""CRM Phase 7: catalogue & activity-based pricing.

- price_list_items gains customer_id (true per-customer override) and
  valid_from/valid_to (item-level date window, independent of the list's).
- new price_history table, written whenever a price_list_item's unit_price
  changes.
- new crm_lead_products join table (structured lead -> product interest,
  replacing the free-text-only "Catalogue Sent" label).
- crm_quote_items gains additive erp_product_id/erp_variant_id columns
  pointing at the real ERP product master, alongside the existing
  crm_products-based product_id (left untouched — no breaking migration of
  historical CRM quote data).

Revision ID: 026_crm_pricing
Revises: 025_crm_ad_spend_fields
"""
from alembic import op

revision = "026_crm_pricing"
down_revision = "025_crm_ad_spend_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE price_list_items ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE price_list_items ADD COLUMN IF NOT EXISTS valid_from DATE")
    op.execute("ALTER TABLE price_list_items ADD COLUMN IF NOT EXISTS valid_to DATE")

    op.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id         UUID NOT NULL REFERENCES companies(id),
            product_id         UUID NOT NULL REFERENCES products(id),
            variant_id         UUID REFERENCES product_variants(id),
            price_list_item_id UUID REFERENCES price_list_items(id) ON DELETE SET NULL,
            old_price          NUMERIC(15, 2),
            new_price          NUMERIC(15, 2) NOT NULL,
            changed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
            changed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_price_history_product ON price_history(product_id, variant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_products (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id              UUID NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
            product_id           UUID REFERENCES products(id) ON DELETE SET NULL,
            variant_id           UUID REFERENCES product_variants(id) ON DELETE SET NULL,
            quantity_interested  NUMERIC(15, 4),
            notes                TEXT,
            created_by           UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_lead_products_lead_id ON crm_lead_products(lead_id)")

    op.execute("ALTER TABLE crm_quote_items ADD COLUMN IF NOT EXISTS erp_product_id UUID REFERENCES products(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE crm_quote_items ADD COLUMN IF NOT EXISTS erp_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE crm_quote_items DROP COLUMN IF EXISTS erp_variant_id")
    op.execute("ALTER TABLE crm_quote_items DROP COLUMN IF EXISTS erp_product_id")
    op.execute("DROP TABLE IF EXISTS crm_lead_products")
    op.execute("DROP TABLE IF EXISTS price_history")
    op.execute("ALTER TABLE price_list_items DROP COLUMN IF EXISTS valid_to")
    op.execute("ALTER TABLE price_list_items DROP COLUMN IF EXISTS valid_from")
    op.execute("ALTER TABLE price_list_items DROP COLUMN IF EXISTS customer_id")
