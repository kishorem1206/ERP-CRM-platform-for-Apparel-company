"""CRM Phase 8: WhatsApp automation rules + send logs.

- new whatsapp_automation_rules table: configurable trigger_event,
  template_id OR freeform message_body with {{var}} placeholders,
  recipient_type, delay_minutes, is_active — no hard-coded messages.
- new whatsapp_automation_logs table: per-send audit trail (status
  sent/failed/skipped_no_phone/skipped_disabled), since real Meta
  credentials are not configured yet and failures must stay visible.

Revision ID: 027_whatsapp_automation
Revises: 026_crm_pricing
"""
from alembic import op

revision = "027_whatsapp_automation"
down_revision = "026_crm_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_automation_rules (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id      UUID NOT NULL REFERENCES companies(id),
            name            VARCHAR(200) NOT NULL,
            trigger_event   VARCHAR(50) NOT NULL,
            template_id     UUID REFERENCES whatsapp_templates(id) ON DELETE SET NULL,
            message_body    TEXT,
            recipient_type  VARCHAR(20) NOT NULL,
            delay_minutes   INTEGER NOT NULL DEFAULT 0,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_whatsapp_automation_rules_company_trigger ON whatsapp_automation_rules(company_id, trigger_event)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_automation_logs (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_id          UUID NOT NULL REFERENCES whatsapp_automation_rules(id) ON DELETE CASCADE,
            lead_id          UUID REFERENCES crm_leads(id) ON DELETE SET NULL,
            recipient_phone  VARCHAR(50),
            rendered_body    TEXT,
            status           VARCHAR(30) NOT NULL,
            error_message    TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_whatsapp_automation_logs_rule_id ON whatsapp_automation_logs(rule_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_whatsapp_automation_logs_lead_id ON whatsapp_automation_logs(lead_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS whatsapp_automation_logs")
    op.execute("DROP TABLE IF EXISTS whatsapp_automation_rules")
