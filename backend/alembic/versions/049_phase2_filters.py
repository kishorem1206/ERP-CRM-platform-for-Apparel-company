"""Phase 2 of the 16-item request: warehouse material-type filtering,
vendor-product filtering, and a real Products link on packaging materials.

- warehouses.material_type: NULL = general warehouse (no filtering), or one
  of the PRODUCT_TYPES values to restrict material dropdowns sourced from it.
- vendors.supplies_product_types: NULL/empty = unrestricted (shows all
  products), otherwise an array of PRODUCT_TYPES this vendor is known to
  supply, used to filter the product dropdown once a vendor is selected.
- style_packing_materials.product_id: same "link instead of duplicate" fix
  already applied to inventory_lots.product_id/brand_id and style_trims.lot_id
  — lets a packing material be picked from the Products catalog (product_type
  'packing') instead of typed as free text.

Revision ID: 049_phase2_filters
Revises: 048_brand_links
"""
from alembic import op

revision = "049_phase2_filters"
down_revision = "048_brand_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE warehouses ADD COLUMN material_type VARCHAR(30)")
    op.execute("ALTER TABLE vendors ADD COLUMN supplies_product_types TEXT[]")
    op.execute("ALTER TABLE style_packing_materials ADD COLUMN product_id UUID REFERENCES products(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE lot_packing_materials ADD COLUMN product_id UUID REFERENCES products(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE lot_packing_materials DROP COLUMN product_id")
    op.execute("ALTER TABLE style_packing_materials DROP COLUMN product_id")
    op.execute("ALTER TABLE vendors DROP COLUMN supplies_product_types")
    op.execute("ALTER TABLE warehouses DROP COLUMN material_type")
