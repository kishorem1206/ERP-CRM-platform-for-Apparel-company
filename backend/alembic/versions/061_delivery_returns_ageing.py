"""Production Module Reorganisation Phase 10 — Delivery Challan, Returns,
Inventory and GST.

The existing `Delivery`/`DeliveryItem` (sales.py) already is the
customer-facing outward-movement document the spec calls "Delivery
Challan" (it already has its own PDF) — this migration extends it
(purpose of movement, per-item returnable flag, per-item weight) rather
than creating a second, competing "outward movement" entity, since the
Phase 0 audit's own rule 5 warns against duplicate workflows. The
existing job-work challan (`ProductionStageChallan` / services/
delivery_challan.py) is untouched; it serves a different audience
(vendor/worker) and is not renamed or merged.

GST/HSN is reused as-is (`HsnCode`, `TaxService.determine_tax`) — no new
tax config is introduced. Sales Returns (`sales_returns`/
`sales_return_items`) is genuinely new — nothing in the schema modeled a
customer returning finished goods before this. Double-credit protection
mirrors the existing MIS-return pattern (production.py) at the
application layer: a return line optionally references the
`delivery_item_id` it came from, and the service layer checks cumulative
returned qty against that line's delivered qty before accepting a new
return — no DB constraint is needed for this because "already returned"
is a SUM, not a single column.

Inventory ageing (`stock_ageing`) gains manual date-correction columns on
`inventory_transactions` (`corrected_date`, who/when) and becomes
lot-aware in the service-layer query (Phase 10 report) instead of only
ever using the single earliest-ever receipt date per product+warehouse.

Revision ID: 061_delivery_returns_ageing
Revises: 060_stage_size_tracking
"""
from alembic import op

revision = "061_delivery_returns_ageing"
down_revision = "060_stage_size_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE deliveries ADD COLUMN purpose VARCHAR(30) NOT NULL DEFAULT 'sale'")
    op.execute("ALTER TABLE delivery_items ADD COLUMN returnable BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE delivery_items ADD COLUMN weight_kg NUMERIC(10,3)")

    op.execute("""
        CREATE TABLE sales_returns (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL REFERENCES companies(id),
            return_number VARCHAR(50) NOT NULL,
            delivery_id UUID REFERENCES deliveries(id),
            customer_id UUID NOT NULL REFERENCES customers(id),
            return_date DATE NOT NULL,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'completed',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            created_by UUID REFERENCES users(id)
        )
    """)
    op.execute("CREATE UNIQUE INDEX ux_sales_returns_company_number ON sales_returns(company_id, return_number)")

    op.execute("""
        CREATE TABLE sales_return_items (
            id UUID PRIMARY KEY,
            sales_return_id UUID NOT NULL REFERENCES sales_returns(id) ON DELETE CASCADE,
            delivery_item_id UUID REFERENCES delivery_items(id),
            product_id UUID NOT NULL REFERENCES products(id),
            variant_id UUID REFERENCES product_variants(id),
            quantity NUMERIC(15,4) NOT NULL,
            unit_id UUID NOT NULL REFERENCES units(id),
            disposition VARCHAR(20) NOT NULL,
            unit_cost NUMERIC(15,2),
            total_cost NUMERIC(15,2),
            inv_transaction_id UUID REFERENCES inventory_transactions(id),
            notes TEXT
        )
    """)

    op.execute("ALTER TABLE inventory_transactions ADD COLUMN corrected_date DATE")
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN date_corrected_by UUID REFERENCES users(id)")
    op.execute("ALTER TABLE inventory_transactions ADD COLUMN date_corrected_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN date_corrected_at")
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN date_corrected_by")
    op.execute("ALTER TABLE inventory_transactions DROP COLUMN corrected_date")
    op.execute("DROP TABLE sales_return_items")
    op.execute("DROP TABLE sales_returns")
    op.execute("ALTER TABLE delivery_items DROP COLUMN weight_kg")
    op.execute("ALTER TABLE delivery_items DROP COLUMN returnable")
    op.execute("ALTER TABLE deliveries DROP COLUMN purpose")
