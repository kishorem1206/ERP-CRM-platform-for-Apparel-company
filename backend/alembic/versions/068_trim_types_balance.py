"""Trim types, trims per stage, cutting balance fabric, per-piece materials.

- style_trims / lot_trims.trim_type: Elastic, Thread / Cone, Label, ...
  Existing rows get a type guessed from their name where it's obvious.
- lot_trims.stage_id: the lot stage a trim is used in, from the style
  trim's process; backfilled for existing lots.
- production_stage_entries.balance_kg / balance_action: fabric left over
  after cutting, and whether it went back to the warehouse or was wasted.
- lot_materials.per_piece_qty: how much of the material one piece takes,
  so a quantity can be worked out for any number of pieces.

Revision ID: 068_trim_types_balance
Revises: 067_stage_skip_missing
"""
from alembic import op

revision = "068_trim_types_balance"
down_revision = "067_stage_skip_missing"
branch_labels = None
depends_on = None

_GUESS = """
    CASE
        WHEN {c} ILIKE '%elastic%' THEN 'Elastic'
        WHEN {c} ILIKE '%thread%' OR {c} ILIKE '%cone%' THEN 'Thread / Cone'
        WHEN {c} ILIKE '%zip%' THEN 'Zipper'
        WHEN {c} ILIKE '%button%' THEN 'Button'
        WHEN {c} ILIKE '%label%' THEN 'Label'
        WHEN {c} ILIKE '%tag%' THEN 'Tag'
        WHEN {c} ILIKE '%tape%' THEN 'Tape'
        WHEN {c} ILIKE '%lace%' THEN 'Lace'
        WHEN {c} ILIKE '%drawcord%' OR {c} ILIKE '%draw cord%' OR {c} ILIKE '%string%' THEN 'Drawcord'
        WHEN {c} ILIKE '%interlin%' OR {c} ILIKE '%fusing%' THEN 'Interlining'
        WHEN {c} ILIKE '%velcro%' THEN 'Velcro'
        WHEN {c} ILIKE '%rivet%' OR {c} ILIKE '%snap%' OR {c} ILIKE '%eyelet%' THEN 'Snap / Rivet / Eyelet'
        WHEN {c} ILIKE '%patch%' OR {c} ILIKE '%badge%' THEN 'Patch / Badge'
        WHEN {c} ILIKE '%piping%' THEN 'Piping'
    END
"""


def upgrade() -> None:
    op.execute("ALTER TABLE style_trims ADD COLUMN IF NOT EXISTS trim_type VARCHAR(50)")
    op.execute("ALTER TABLE lot_trims ADD COLUMN IF NOT EXISTS trim_type VARCHAR(50)")
    op.execute("ALTER TABLE lot_trims ADD COLUMN IF NOT EXISTS stage_id UUID REFERENCES production_stages(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE production_stage_entries ADD COLUMN IF NOT EXISTS balance_kg NUMERIC(10, 3)")
    op.execute("ALTER TABLE production_stage_entries ADD COLUMN IF NOT EXISTS balance_action VARCHAR(10)")
    op.execute("ALTER TABLE lot_materials ADD COLUMN IF NOT EXISTS per_piece_qty NUMERIC(15, 6)")

    op.execute(f"UPDATE style_trims SET trim_type = {_GUESS.format(c='trim_name')} WHERE trim_type IS NULL")
    op.execute(f"UPDATE lot_trims SET trim_type = {_GUESS.format(c='trim_name')} WHERE trim_type IS NULL")
    op.execute("""
        UPDATE lot_trims lt SET stage_id = ps.id
        FROM style_trims st, style_processes sp, production_stages ps
        WHERE lt.style_trim_id = st.id AND st.process_seq IS NOT NULL
          AND sp.style_id = st.style_id AND sp.seq = st.process_seq
          AND ps.production_lot_id = lt.production_lot_id AND ps.style_process_id = sp.id
          AND lt.stage_id IS NULL
    """)
    op.execute("""
        UPDATE lot_materials lm SET per_piece_qty = lm.planned_qty / pl.planned_qty
        FROM production_lots pl
        WHERE pl.id = lm.production_lot_id AND lm.planned_qty IS NOT NULL
          AND pl.planned_qty > 0 AND lm.per_piece_qty IS NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE lot_materials DROP COLUMN IF EXISTS per_piece_qty")
    op.execute("ALTER TABLE production_stage_entries DROP COLUMN IF EXISTS balance_action")
    op.execute("ALTER TABLE production_stage_entries DROP COLUMN IF EXISTS balance_kg")
    op.execute("ALTER TABLE lot_trims DROP COLUMN IF EXISTS stage_id")
    op.execute("ALTER TABLE lot_trims DROP COLUMN IF EXISTS trim_type")
    op.execute("ALTER TABLE style_trims DROP COLUMN IF EXISTS trim_type")
