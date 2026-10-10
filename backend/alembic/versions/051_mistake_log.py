"""Phase 3 item #15 of the 16-item request: a per-lot Mistake Log —
Staff / Process / Description / Problem / Action Taken — kept for future
reference and documentation.

Revision ID: 051_mistake_log
Revises: 050_lot_status_simplify
"""
from alembic import op

revision = "051_mistake_log"
down_revision = "050_lot_status_simplify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE production_mistake_logs (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL REFERENCES companies(id),
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            stage_id UUID REFERENCES production_stages(id) ON DELETE SET NULL,
            process_name VARCHAR(100),
            staff_id UUID REFERENCES internal_workers(id) ON DELETE SET NULL,
            staff_name VARCHAR(200),
            mistake_date DATE NOT NULL,
            description TEXT NOT NULL,
            problem_type VARCHAR(100),
            action_taken TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            created_by UUID REFERENCES users(id)
        )
    """)
    op.execute("CREATE INDEX ix_production_mistake_logs_lot ON production_mistake_logs(production_lot_id)")


def downgrade() -> None:
    op.execute("DROP TABLE production_mistake_logs")
