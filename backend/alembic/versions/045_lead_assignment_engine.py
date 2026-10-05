"""Phase 2 Step 1-2: smart lead assignment (round-robin + rule-based), and the
fields response-time tracking and overdue escalation (Steps 8-9) need.

- crm_lead_assignment_rules: ordered, company-scoped rules. First active
  match wins. Conditions are plain optional-field AND (no expression
  engine) - source / minimum score / location tier -> assign_to one user.
  "Assign to Team A" from the spec maps to assign_to a specific employee
  here, since this codebase has no Team/group entity to assign to instead
  (confirmed during the Phase 1 audit) - not invented here either.
- crm_lead_assignment_pool + crm_round_robin_state: the round-robin
  candidate list and a single-row-per-company cursor of who was assigned
  last, so the next unmatched lead goes to the next person in turn.
- crm_leads additions: first_contacted_at (distinct from the existing
  last_contacted_at, which gets overwritten on every contact - this one is
  set once), response_target_at (the deadline implied by priority),
  escalation_employee_notified_at / escalation_manager_notified_at (so the
  escalation job never re-notifies for the same lead - idempotency, spec
  Step 18).
- companies additions: configurable response-time targets and escalation
  delays, same pattern as the existing bill_alert_days/lead_score_* settings.

Revision ID: 045_lead_assignment_engine
Revises: 044_lead_scoring_rules
"""
from alembic import op

revision = "045_lead_assignment_engine"
down_revision = "044_lead_scoring_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_assignment_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            name VARCHAR(200) NOT NULL,
            sort_order SMALLINT NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            source_id UUID NULL REFERENCES crm_lead_sources(id) ON DELETE SET NULL,
            min_score SMALLINT NULL,
            location_tier VARCHAR(20) NULL,
            assign_to UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_assignment_pool (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sort_order SMALLINT NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (company_id, user_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_round_robin_state (
            company_id UUID PRIMARY KEY REFERENCES companies(id),
            last_assigned_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("ALTER TABLE crm_leads ADD COLUMN first_contacted_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN response_target_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN escalation_employee_notified_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE crm_leads ADD COLUMN escalation_manager_notified_at TIMESTAMPTZ NULL")

    op.execute("ALTER TABLE companies ADD COLUMN response_target_high_minutes SMALLINT NOT NULL DEFAULT 30")
    op.execute("ALTER TABLE companies ADD COLUMN response_target_medium_hours SMALLINT NOT NULL DEFAULT 24")
    op.execute("ALTER TABLE companies ADD COLUMN response_target_low_hours SMALLINT NOT NULL DEFAULT 72")
    op.execute("ALTER TABLE companies ADD COLUMN escalation_employee_hours SMALLINT NOT NULL DEFAULT 2")
    op.execute("ALTER TABLE companies ADD COLUMN escalation_manager_hours SMALLINT NOT NULL DEFAULT 4")


def downgrade() -> None:
    op.execute("ALTER TABLE companies DROP COLUMN escalation_manager_hours")
    op.execute("ALTER TABLE companies DROP COLUMN escalation_employee_hours")
    op.execute("ALTER TABLE companies DROP COLUMN response_target_low_hours")
    op.execute("ALTER TABLE companies DROP COLUMN response_target_medium_hours")
    op.execute("ALTER TABLE companies DROP COLUMN response_target_high_minutes")

    op.execute("ALTER TABLE crm_leads DROP COLUMN escalation_manager_notified_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN escalation_employee_notified_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN response_target_at")
    op.execute("ALTER TABLE crm_leads DROP COLUMN first_contacted_at")

    op.execute("DROP TABLE crm_round_robin_state")
    op.execute("DROP TABLE crm_lead_assignment_pool")
    op.execute("DROP TABLE crm_lead_assignment_rules")
