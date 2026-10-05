"""Lead Intelligence Phase 1: scoring rules + service areas (admin-configurable, spec Step 22).

- crm_lead_scoring_rules: one row per scoring rule, company-scoped, each
  with a stable `code` the scoring engine references in code, a `weight`
  an admin can edit, and `is_active` to turn a rule off without deleting
  its history. Seeded with the spec's own example weights (Step 14) for
  every existing company - explicitly starting weights, not fixed business
  rules; admins can change every one of them from day one.
- crm_lead_service_areas: configurable preferred/secondary/non-serviceable
  locations (spec Step 7). Seeded empty - every location is untiered
  ("other") until a company configures its own list, so this never
  penalizes a company that hasn't set it up yet.

Revision ID: 044_lead_scoring_rules
Revises: 043_lead_intelligence_schema
"""
from alembic import op

revision = "044_lead_scoring_rules"
down_revision = "043_lead_intelligence_schema"
branch_labels = None
depends_on = None

# (category, code, label, weight) - spec Step 14's example weights verbatim.
DEFAULT_RULES = [
    ("requirement", "requirement.quantity_specified", "Specific quantity mentioned", 20),
    ("requirement", "requirement.product_specified", "Specific product/category mentioned", 10),
    ("requirement", "requirement.detailed", "Detailed requirement description", 10),
    ("intent", "intent.direct_enquiry", "Direct enquiry / phone contact", 15),
    ("intent", "intent.quotation_request", "Quotation requested", 15),
    ("intent", "intent.sample_request", "Sample requested", 15),
    ("intent", "intent.catalogue_request", "Generic catalogue request", 5),
    ("contact", "contact.valid_phone", "Valid phone number", 10),
    ("contact", "contact.valid_email", "Valid email address", 5),
    ("contact", "contact.business_email", "Business email domain", 5),
    ("contact", "contact.missing_phone", "Phone number missing", -15),
    ("business", "business.company_identified", "Company name identified", 5),
    ("business", "business.gst_available", "GST number available", 5),
    ("location", "location.preferred", "Preferred service area", 10),
    ("location", "location.secondary", "Secondary service area", 5),
    ("location", "location.non_serviceable", "Outside serviceable area", -10),
    ("repeat", "repeat.previous_enquiry", "Repeat contact — previous enquiry found", 15),
    ("quality", "quality.detailed_message", "Detailed, high-quality message", 10),
    ("quality", "quality.vague_message", "Very vague message", 0),
]


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_scoring_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            category VARCHAR(30) NOT NULL,
            code VARCHAR(50) NOT NULL,
            label VARCHAR(200) NOT NULL,
            weight SMALLINT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (company_id, code)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lead_service_areas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id),
            location_name VARCHAR(200) NOT NULL,
            tier VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (company_id, location_name)
        )
    """)

    for category, code, label, weight in DEFAULT_RULES:
        op.execute(
            f"""
            INSERT INTO crm_lead_scoring_rules (id, company_id, category, code, label, weight, created_at, updated_at)
            SELECT gen_random_uuid(), c.id, '{category}', '{code}', '{label}', {weight}, now(), now()
            FROM companies c
            ON CONFLICT (company_id, code) DO NOTHING
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE crm_lead_service_areas")
    op.execute("DROP TABLE crm_lead_scoring_rules")
