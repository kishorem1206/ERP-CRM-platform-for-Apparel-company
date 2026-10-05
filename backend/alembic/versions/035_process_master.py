"""Upgrade #2 Phase 2: Process Master.

- process_masters: reusable process definitions (Knitting, Cutting,
  Making, ...) with default rate/unit/tolerance, selectable from a
  dropdown instead of style_processes.process_name being pure free text.
- style_processes.process_master_id - optional link; style-specific
  values always override the master's defaults.
- Seeds the 12 standard process names for every EXISTING company (seeding
  is one-time and won't retroactively reach already-seeded companies).

Revision ID: 035_process_master
Revises: 034_style_product_link
"""
from alembic import op

revision = "035_process_master"
down_revision = "034_style_product_link"
branch_labels = None
depends_on = None

PROCESS_NAMES = [
    "Knitting", "Dyeing", "Compacting", "Printing", "Cutting", "Making",
    "Fusing", "Stitching", "Trimming", "Checking", "Ironing", "Packing",
]


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS process_masters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            name VARCHAR(100) NOT NULL,
            default_unit VARCHAR(30),
            default_tolerance_pct NUMERIC(5, 2),
            default_min_rate NUMERIC(15, 2),
            default_max_rate NUMERIC(15, 2),
            default_planned_rate NUMERIC(15, 2),
            sort_order SMALLINT NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (company_id, name)
        )
    """)
    op.execute("ALTER TABLE style_processes ADD COLUMN process_master_id UUID NULL REFERENCES process_masters(id)")

    for i, name in enumerate(PROCESS_NAMES):
        op.execute(
            f"""
            INSERT INTO process_masters (id, company_id, name, sort_order, created_at)
            SELECT gen_random_uuid(), c.id, '{name}', {i}, now()
            FROM companies c
            ON CONFLICT (company_id, name) DO NOTHING
            """
        )


def downgrade() -> None:
    op.execute("ALTER TABLE style_processes DROP COLUMN process_master_id")
    op.execute("DROP TABLE process_masters")
