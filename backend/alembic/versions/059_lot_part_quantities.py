"""Production Module Reorganisation Phase 8 — Production Lot Creation and
Material Issue.

The source document's own hierarchy diagram is Order -> Style -> Part ->
Colour -> Size -> Planned Quantity -> Material Requirements. Phase 1 built
the Style-level half of this (StylePartColour/StylePartSize, the
blueprint template); this closes the LOT-level half — the actual order's
own planned quantities per (part, colour, size), pre-filled from the
Style's template at lot creation and explicitly overridable per lot, the
same convention ProductionLotSize already uses for the plain size
dimension. Also adds an idempotency key to Material Issue so a network
retry or duplicate submission can't issue the same stock twice.

Revision ID: 059_lot_part_quantities
Revises: 058_wages_operations
"""
from alembic import op

revision = "059_lot_part_quantities"
down_revision = "058_wages_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE lot_part_colours (
            id UUID PRIMARY KEY,
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            style_part_colour_id UUID REFERENCES style_part_colours(id),
            style_part_id UUID NOT NULL REFERENCES style_parts(id),
            colour_id UUID REFERENCES colours(id) ON DELETE SET NULL,
            sort_order SMALLINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_lot_part_colours_lot ON lot_part_colours(production_lot_id)")
    op.execute("""
        CREATE TABLE lot_part_sizes (
            id UUID PRIMARY KEY,
            lot_part_colour_id UUID NOT NULL REFERENCES lot_part_colours(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            planned_qty INTEGER NOT NULL DEFAULT 0,
            sort_order SMALLINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX ix_lot_part_sizes_part_colour ON lot_part_sizes(lot_part_colour_id)")

    op.execute("ALTER TABLE material_issues ADD COLUMN idempotency_key VARCHAR(100)")
    op.execute(
        "CREATE UNIQUE INDEX ux_material_issues_idempotency "
        "ON material_issues(company_id, idempotency_key) WHERE idempotency_key IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ux_material_issues_idempotency")
    op.execute("ALTER TABLE material_issues DROP COLUMN idempotency_key")
    op.execute("DROP TABLE lot_part_sizes")
    op.execute("DROP TABLE lot_part_colours")
