"""style master — full production blueprint per Garments_ERP_Style_Master_Specification

Revision ID: 009_style_master
Revises: 008_crm_phase5
Create Date: 2026-09-05

Implements the Style Master as the production blueprint (see
Garments_ERP_Style_Master_Specification.md): configurable process workflow
with per-process tolerance/units/rates/sub-processes, size & colour
variants, and yarn/fabric/trim/packing-material planning referencing the
materials masters. Also adds snapshot columns to production_stages /
production_lots so a LOT freezes the Style configuration at creation time
(edits to the Style must not retroactively change existing LOTs).
"""
from alembic import op

revision = "009_style_master"
down_revision = "008_crm_phase5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── styles — extend with versioning / lifecycle columns ───────────────────
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS final_output_unit VARCHAR(30)")
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ")
    op.execute("ALTER TABLE styles ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id)")

    # ── style_sizes — applicable size chart (references Size Master) ──────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_sizes (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id    UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            size_id     UUID NOT NULL REFERENCES sizes(id),
            sort_order  SMALLINT NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_sizes_style ON style_sizes(style_id)")

    # ── style_colours — applicable colours (references Colour Master) ─────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_colours (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id    UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            colour_id   UUID NOT NULL REFERENCES colours(id),
            sort_order  SMALLINT NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_colours_style ON style_colours(style_id)")

    # ── style_yarns — yarn requirements (references Yarn Master / lots) ───────
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_yarns (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id    UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            yarn_name   VARCHAR(200) NOT NULL,
            lot_id      UUID REFERENCES inventory_lots(id),
            quantity    NUMERIC(15,4),
            unit        VARCHAR(30),
            notes       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_yarns_style ON style_yarns(style_id)")

    # ── style_fabrics — fabric requirements (references Fabric Master / lots) ─
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_fabrics (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id      UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            fabric_name   VARCHAR(200) NOT NULL,
            lot_id        UUID REFERENCES inventory_lots(id),
            consumption   NUMERIC(15,4),
            unit          VARCHAR(30),
            excess_pct    NUMERIC(5,2),
            notes         TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_fabrics_style ON style_fabrics(style_id)")

    # ── style_processes — configurable workflow (NOT a hard-coded sequence) ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_processes (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id          UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            seq               SMALLINT NOT NULL DEFAULT 0,
            process_name      VARCHAR(100) NOT NULL,
            is_enabled        BOOLEAN NOT NULL DEFAULT true,
            tolerance_pct     NUMERIC(5,2),
            input_unit        VARCHAR(30),
            output_unit       VARCHAR(30),
            conversion_rule   VARCHAR(200),
            min_rate          NUMERIC(15,2),
            max_rate          NUMERIC(15,2),
            planned_rate      NUMERIC(15,2),
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_processes_style ON style_processes(style_id)")

    # ── style_sub_processes — e.g. Stitching > Power Table / Snitex / Helpers ─
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_sub_processes (
            id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_process_id   UUID NOT NULL REFERENCES style_processes(id) ON DELETE CASCADE,
            seq                SMALLINT NOT NULL DEFAULT 0,
            name               VARCHAR(100) NOT NULL,
            notes              TEXT,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_sub_processes_process ON style_sub_processes(style_process_id)")

    # ── style_trims — trim planning (references Trim Master / lots) ───────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_trims (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id     UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            trim_name    VARCHAR(200) NOT NULL,
            lot_id       UUID REFERENCES inventory_lots(id),
            quantity     NUMERIC(15,4),
            unit         VARCHAR(30),
            category     VARCHAR(30),
            excess_pct   NUMERIC(5,2),
            notes        TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_trims_style ON style_trims(style_id)")

    # ── style_packing_materials — packing material planning ────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS style_packing_materials (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            style_id            UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
            material_name       VARCHAR(200) NOT NULL,
            quantity            NUMERIC(15,4),
            unit                VARCHAR(30),
            excess_pct          NUMERIC(5,2),
            consumption_stage   VARCHAR(50),
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_style_packing_materials_style ON style_packing_materials(style_id)")

    # ── production_stages — snapshot columns so a LOT freezes Style config ────
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS tolerance_pct NUMERIC(5,2)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS input_unit VARCHAR(30)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS output_unit VARCHAR(30)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS conversion_rule VARCHAR(200)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS min_rate NUMERIC(15,2)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS max_rate NUMERIC(15,2)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS planned_rate NUMERIC(15,2)")
    op.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS style_process_id UUID REFERENCES style_processes(id)")

    # ── production_lots — snapshot of the style's final output unit ───────────
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS final_output_unit VARCHAR(30)")
    op.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS style_version INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS style_version")
    op.execute("ALTER TABLE production_lots DROP COLUMN IF EXISTS final_output_unit")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS style_process_id")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS planned_rate")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS max_rate")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS min_rate")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS conversion_rule")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS output_unit")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS input_unit")
    op.execute("ALTER TABLE production_stages DROP COLUMN IF EXISTS tolerance_pct")
    op.execute("DROP TABLE IF EXISTS style_packing_materials")
    op.execute("DROP TABLE IF EXISTS style_trims")
    op.execute("DROP TABLE IF EXISTS style_sub_processes")
    op.execute("DROP TABLE IF EXISTS style_processes")
    op.execute("DROP TABLE IF EXISTS style_fabrics")
    op.execute("DROP TABLE IF EXISTS style_yarns")
    op.execute("DROP TABLE IF EXISTS style_colours")
    op.execute("DROP TABLE IF EXISTS style_sizes")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS created_by")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS final_output_unit")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE styles DROP COLUMN IF EXISTS version")
