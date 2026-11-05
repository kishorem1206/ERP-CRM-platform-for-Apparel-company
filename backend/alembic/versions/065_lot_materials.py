"""Materials planned for a production lot.

A lot's material list is set at its start (pre-filled from the Style's BOM,
then edited), and Material Issue Slips are raised against it. Issued
quantities stay on the slips; this table holds only what is planned.

Revision ID: 065_lot_materials
Revises: 064_scheduled_job_runs
"""
from alembic import op

revision = "065_lot_materials"
down_revision = "064_scheduled_job_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE lot_materials (
            id UUID PRIMARY KEY,
            production_lot_id UUID NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id),
            unit_id UUID REFERENCES units(id),
            planned_qty NUMERIC(15, 4),
            notes TEXT,
            sort_order SMALLINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ,
            CONSTRAINT uq_lot_materials_lot_product UNIQUE (production_lot_id, product_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE lot_materials")
