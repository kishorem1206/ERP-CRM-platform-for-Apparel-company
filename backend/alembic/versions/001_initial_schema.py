"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-25

Baseline migration — applies the full schema using IF NOT EXISTS / IF NOT EXISTS guards
so it is safe to run against both a brand-new database and an existing one that was
bootstrapped via schema.sql.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name                    VARCHAR(200) NOT NULL,
            gstin                   VARCHAR(15),
            pan                     VARCHAR(10),
            address                 TEXT,
            city                    VARCHAR(100),
            state                   VARCHAR(100),
            state_code              SMALLINT,
            pincode                 VARCHAR(10),
            phone                   VARCHAR(20),
            email                   VARCHAR(200),
            website                 VARCHAR(200),
            logo_url                TEXT,
            currency                VARCHAR(3) DEFAULT 'INR',
            default_hsn             VARCHAR(8),
            fabric_variance_pct     NUMERIC(5,2) DEFAULT 3.00,
            cost_of_capital_pct     NUMERIC(5,2),
            negative_stock_allowed  BOOLEAN DEFAULT false,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id          UUID NOT NULL REFERENCES companies(id),
            email               VARCHAR(200) NOT NULL,
            hashed_password     VARCHAR(200) NOT NULL,
            full_name           VARCHAR(200),
            phone               VARCHAR(20),
            is_active           BOOLEAN NOT NULL DEFAULT true,
            is_owner            BOOLEAN NOT NULL DEFAULT false,
            last_login_at       TIMESTAMPTZ,
            failed_login_count  SMALLINT DEFAULT 0,
            locked_until        TIMESTAMPTZ,
            totp_secret         VARCHAR(64),
            totp_enabled        BOOLEAN NOT NULL DEFAULT false,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (company_id, email)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id  UUID NOT NULL REFERENCES companies(id),
            name        VARCHAR(100) NOT NULL,
            description TEXT,
            is_system   BOOLEAN DEFAULT false,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (company_id, name)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            code        VARCHAR(100) NOT NULL UNIQUE,
            description VARCHAR(300)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, role_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  VARCHAR(200) NOT NULL UNIQUE,
            expires_at  TIMESTAMPTZ NOT NULL,
            revoked_at  TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # --- remaining tables follow the same IF NOT EXISTS pattern ---

    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id          UUID NOT NULL REFERENCES companies(id),
            user_id             UUID REFERENCES users(id),
            notification_type   VARCHAR(50) NOT NULL,
            title               VARCHAR(200) NOT NULL,
            body                TEXT NOT NULL,
            data                JSONB,
            is_read             BOOLEAN NOT NULL DEFAULT false,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at DESC)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS file_attachments (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id  UUID NOT NULL REFERENCES companies(id),
            entity_type VARCHAR(50) NOT NULL,
            entity_id   UUID NOT NULL,
            file_name   VARCHAR(300) NOT NULL,
            file_url    TEXT NOT NULL,
            file_size   INTEGER,
            mime_type   VARCHAR(100),
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            uploaded_by UUID REFERENCES users(id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_attachments_entity ON file_attachments(entity_type, entity_id)")

    # Users totp columns (safe on existing DBs)
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count SMALLINT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ")

    # Performance indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")


def downgrade() -> None:
    # Downgrade intentionally left as a no-op for the baseline migration.
    # To reset the database, drop and recreate it via docker-compose.
    pass
