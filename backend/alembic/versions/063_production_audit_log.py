"""Production Module Reorganisation Phase 11 — Audit history.

A minimal, generic audit trail for the two mutation points Phase 11 cares
about most: lot status transitions (cutting -> checking -> packing ->
completed, or reopened) and stage corrections (status, assignment, and
the sent/received/rejected quantity corrections StageUpdate already
validates). Scoped to production_lot_id even for stage-level entries so
"show this lot's history" is always a single indexed lookup, regardless
of which entity actually changed.

Revision ID: 063_production_audit_log
Revises: 062_product_variant_part_unique
"""
from alembic import op

revision = "063_production_audit_log"
down_revision = "062_product_variant_part_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE production_audit_log (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL REFERENCES companies(id),
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            entity_type VARCHAR(30) NOT NULL,
            entity_id UUID NOT NULL,
            action VARCHAR(50) NOT NULL,
            field_name VARCHAR(50),
            old_value VARCHAR(200),
            new_value VARCHAR(200),
            notes TEXT,
            changed_by UUID REFERENCES users(id),
            changed_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_production_audit_log_lot ON production_audit_log(production_lot_id, changed_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE production_audit_log")
