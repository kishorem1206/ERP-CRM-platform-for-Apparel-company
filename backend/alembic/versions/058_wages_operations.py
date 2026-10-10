"""Production Module Reorganisation Phase 7 — Wages and Other Expenses.

Most of this phase's ask already existed:
- Other Expenses, with estimated vs. actual kept separate: StyleAdditionalCost
  (planned, style-level) and LotAdditionalCost (planned_amount/actual_amount,
  lot-level) — already a real planned-vs-actual split.
- Production quantity and order value summaries: LotCostSummaryOut already
  computes total_planned/total_actual/actual_revenue/actual_profit etc.
- Rates by process: StyleProcess already has min_rate/max_rate/planned_rate,
  now also scoped by style part (Phase 5).

The one real gap: "Operations" (StyleSubProcess — e.g. Overlock/Flatlock/
Sinker/Helper under a Stitching process) had no rate fields at all, unlike
their parent process. This adds the same min_rate/max_rate/planned_rate
StyleProcess already has, purely additive.

Revision ID: 058_wages_operations
Revises: 057_bom_consolidation
"""
from alembic import op

revision = "058_wages_operations"
down_revision = "057_bom_consolidation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE style_sub_processes ADD COLUMN min_rate NUMERIC(15, 2)")
    op.execute("ALTER TABLE style_sub_processes ADD COLUMN max_rate NUMERIC(15, 2)")
    op.execute("ALTER TABLE style_sub_processes ADD COLUMN planned_rate NUMERIC(15, 2)")


def downgrade() -> None:
    op.execute("ALTER TABLE style_sub_processes DROP COLUMN planned_rate")
    op.execute("ALTER TABLE style_sub_processes DROP COLUMN max_rate")
    op.execute("ALTER TABLE style_sub_processes DROP COLUMN min_rate")
