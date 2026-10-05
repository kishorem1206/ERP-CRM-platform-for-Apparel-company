"""Upgrade #2 Phase 3: Size Chart Master.

- size_charts / size_chart_items: reusable named size charts with a
  default quantity per size, selectable from Style Creation.
- style_sizes.quantity / size_chart_id - additive. quantity may come
  from a linked chart item's default or a style-specific override
  (override always wins).

Revision ID: 036_size_chart
Revises: 035_process_master
"""
from alembic import op

revision = "036_size_chart"
down_revision = "035_process_master"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS size_charts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (company_id, name)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS size_chart_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            size_chart_id UUID NOT NULL REFERENCES size_charts(id) ON DELETE CASCADE,
            size_id UUID NOT NULL REFERENCES sizes(id),
            quantity NUMERIC(12, 3),
            sort_order SMALLINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("ALTER TABLE style_sizes ADD COLUMN quantity NUMERIC(12, 3)")
    op.execute("ALTER TABLE style_sizes ADD COLUMN size_chart_id UUID NULL REFERENCES size_charts(id)")


def downgrade() -> None:
    op.execute("ALTER TABLE style_sizes DROP COLUMN size_chart_id")
    op.execute("ALTER TABLE style_sizes DROP COLUMN quantity")
    op.execute("DROP TABLE size_chart_items")
    op.execute("DROP TABLE size_charts")
