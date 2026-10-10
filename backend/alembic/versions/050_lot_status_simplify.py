"""Phase 3 item #8 of the 16-item request: replace the Production Lot's
8-value status flow (draft/planned/approved/in_production/qc/packing/
ready_to_dispatch/completed) with a simpler 3-stage one floor staff actually
use: Cutting -> Checking -> Packing -> Completed (cancelled kept as an
escape valve). Data-only migration — `status` has always been a plain
VARCHAR with no CHECK constraint, so this just remaps existing rows:

- draft / planned / approved / in_production -> cutting (all pre-QC work)
- qc -> checking
- ready_to_dispatch -> packing (packing was already done; stays active
  rather than silently becoming "completed", which stamps closed_at)
- packing / completed / cancelled -> unchanged

Revision ID: 050_lot_status_simplify
Revises: 049_phase2_filters
"""
from alembic import op

revision = "050_lot_status_simplify"
down_revision = "049_phase2_filters"
branch_labels = None
depends_on = None

_UP = {
    "draft": "cutting", "planned": "cutting", "approved": "cutting", "in_production": "cutting",
    "qc": "checking",
    "ready_to_dispatch": "packing",
}
_DOWN = {
    "cutting": "in_production",
    "checking": "qc",
}


def upgrade() -> None:
    for old, new in _UP.items():
        op.execute(f"UPDATE production_lots SET status = '{new}' WHERE status = '{old}'")


def downgrade() -> None:
    for old, new in _DOWN.items():
        op.execute(f"UPDATE production_lots SET status = '{new}' WHERE status = '{old}'")
