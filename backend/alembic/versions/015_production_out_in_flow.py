"""production workflow — correct OUT/IN semantics, stage-to-stage quantity flow, internal workers

Revision ID: 015_out_in_flow
Revises: 014_finance_fix
Create Date: 2026-09-07

Fixes a real data-model bug: ProductionStage.input_qty/output_qty were being
used for TWO different, conflicting flows — the in-house entry rollup
(ProductionStageEntry.pieces_in/pieces_out, correctly named) and the
outsourced job-work challan rollup, which wrote sent-OUT quantity into
input_qty and received-IN quantity into output_qty (backwards). This
migration gives the challan flow its own columns (sent_qty/received_qty),
leaves input_qty/output_qty exclusively to the in-house entry flow, and adds
assignment_type/worker_id so a stage can be assigned to either a Vendor or a
new Internal Worker master. Backfill preserves existing data's meaning under
the corrected columns rather than discarding it.
"""
from alembic import op

revision = "015_out_in_flow"
down_revision = "014_finance_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS internal_workers (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id    UUID NOT NULL REFERENCES companies(id),
            name          VARCHAR(200) NOT NULL,
            phone         VARCHAR(20),
            role_title    VARCHAR(100),
            daily_rate    NUMERIC(15,2),
            is_active     BOOLEAN NOT NULL DEFAULT true,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by    UUID REFERENCES users(id)
        )
    """)

    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS sent_qty INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS received_qty INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS assignment_type VARCHAR(20)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES internal_workers(id)")

    op.execute("ALTER TABLE production_stage_challans ALTER COLUMN vendor_id DROP NOT NULL")
    op.execute("ALTER TABLE production_stage_challans ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES internal_workers(id)")
    op.execute("ALTER TABLE production_stage_challans ADD COLUMN IF NOT EXISTS rejected_qty INTEGER")

    # Backfill: stages that were assigned a vendor had their challan OUT/IN
    # rolled up (backwards) into input_qty/output_qty — move that data to the
    # correctly-named sent_qty/received_qty so it isn't lost, and mark them.
    op.execute("""
        UPDATE production_stages
        SET assignment_type = 'vendor', sent_qty = input_qty, received_qty = output_qty
        WHERE vendor_id IS NOT NULL
    """)
    op.execute("""
        UPDATE production_stage_challans
        SET rejected_qty = out_qty - COALESCE(in_qty, 0)
        WHERE status = 'received' AND rejected_qty IS NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE production_stage_challans DROP COLUMN IF EXISTS rejected_qty")
    op.execute("ALTER TABLE production_stage_challans DROP COLUMN IF EXISTS worker_id")
    op.execute("ALTER TABLE production_stage_challans ALTER COLUMN vendor_id SET NOT NULL")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS worker_id")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS assignment_type")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS received_qty")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS sent_qty")
    op.execute("DROP TABLE IF EXISTS internal_workers")
