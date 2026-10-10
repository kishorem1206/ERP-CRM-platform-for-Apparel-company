"""Production Module Reorganisation Phase 6 — BOM and Material Requirement
Consolidation.

Fabric and Yarn requirements were the two material categories that never
got a LOT-level snapshot — Trims (lot_trims) and Packing Materials
(lot_packing_materials) already had one, auto-computed at lot creation.
This closes that gap with the same pattern:

- lot_fabrics: required qty computed from StyleFabric's size-wise
  consumption (or flat consumption x lot qty) x excess %, exactly like
  lot_trims.
- lot_yarns: required qty computed as a % of its parent lot_fabrics row's
  required qty (the yarn's consumption_pct from Phase 3's blend
  composition) — so if a fabric needs 1500kg total and a yarn is 65% of
  the blend, that yarn's requirement is 975kg. Yarns not assigned to a
  fabric (freestanding, pre-Phase-3 style) get no automatic quantity.

Both are purely additive snapshots alongside the existing lot_trims/
lot_packing_materials — nothing about them changes existing lot creation
behaviour for lots that predate this phase.

Revision ID: 057_bom_consolidation
Revises: 056_process_routing
"""
from alembic import op

revision = "057_bom_consolidation"
down_revision = "056_process_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE lot_fabrics (
            id UUID PRIMARY KEY,
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            style_fabric_id UUID REFERENCES style_fabrics(id),
            fabric_name VARCHAR(200) NOT NULL,
            style_part_id UUID REFERENCES style_parts(id) ON DELETE SET NULL,
            colour_id UUID REFERENCES colours(id) ON DELETE SET NULL,
            source_type VARCHAR(20),
            unit VARCHAR(30),
            planned_qty NUMERIC(15, 4),
            actual_qty NUMERIC(15, 4),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_lot_fabrics_lot ON lot_fabrics(production_lot_id)")
    op.execute("""
        CREATE TABLE lot_yarns (
            id UUID PRIMARY KEY,
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            lot_fabric_id UUID REFERENCES lot_fabrics(id) ON DELETE CASCADE,
            style_yarn_id UUID REFERENCES style_yarns(id),
            yarn_name VARCHAR(200) NOT NULL,
            colour_id UUID REFERENCES colours(id) ON DELETE SET NULL,
            counts VARCHAR(20),
            consumption_pct NUMERIC(5, 2),
            unit VARCHAR(30),
            planned_qty NUMERIC(15, 4),
            actual_qty NUMERIC(15, 4),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_lot_yarns_lot ON lot_yarns(production_lot_id)")


def downgrade() -> None:
    op.execute("DROP TABLE lot_yarns")
    op.execute("DROP TABLE lot_fabrics")
