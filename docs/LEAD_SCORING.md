# Lead Scoring — Phase 1 Implementation

> Built 2026-10-05. Deterministic, backend-controlled scoring — never delegated to an LLM, per spec Step 23.
> Code: `backend/app/services/lead_intelligence.py`. Migrations: `043_lead_intelligence_schema`, `044_lead_scoring_rules`.

## What runs, and when

A lead is scored once, automatically, right after it's created (`POST /crm/leads`). It is **not** re-scored automatically on every edit — editing a lead's description or linking a person doesn't silently change its score behind someone's back. To recompute, call `POST /crm/leads/{id}/rescore` (there's a button for this on the lead detail page's Lead Intelligence card).

Every score is versioned (`score_version`, currently `1`) and the full breakdown is stored with it (`score_breakdown`), so a score stays explainable even after the rules it was computed under have since changed — the spec's Step 21 requirement.

## Signals and default weights

Scoring rules live in `crm_lead_scoring_rules`, one row per rule per company, fully admin-editable (CRM Settings → Lead Scoring, or `GET/PATCH /crm/scoring-rules`). The weights below are the seeded defaults — the spec's own example weights, verbatim — not fixed business rules.

| Category | Code | Default weight | Fires when |
|---|---|---|---|
| Requirement | `requirement.quantity_specified` | +20 | A linked product has a quantity, or the description contains a number + unit (pcs/kg/dozen/etc.) |
| | `requirement.product_specified` | +10 | At least one product is linked to the lead |
| | `requirement.detailed` | +10 | Description ≥ 60 characters AND quantity or product is specified |
| Intent | `intent.direct_enquiry` | +15 | The linked person has a phone number on file |
| | `intent.quotation_request` | +15 | Description mentions "quotation", "quote", or "price" |
| | `intent.sample_request` | +15 | Description mentions "sample" |
| | `intent.catalogue_request` | +5 | Description mentions "catalogue"/"catalog" |
| Contact | `contact.valid_phone` | +10 | The person's phone normalizes to a plausible 10-digit number |
| | `contact.missing_phone` | -15 | No phone at all (a phone present but unparseable is neither rewarded nor penalized) |
| | `contact.valid_email` | +5 | Email matches a valid shape |
| | `contact.business_email` | +5 | Valid email on a non-free-provider domain (gmail/yahoo/outlook/etc. don't count) |
| Business | `business.company_identified` | +5 | An organization is linked to the lead |
| | `business.gst_available` | +5 | The lead's linked customer (post-conversion) has a GST number — **see limitation below** |
| Location | `location.preferred` | +10 | The person's city matches a company-configured "preferred" service area |
| | `location.secondary` | +5 | Matches a "secondary" service area |
| | `location.non_serviceable` | -10 | Matches a configured "non_serviceable" area |
| Repeat | `repeat.previous_enquiry` | +15 | The same person or organization has an earlier lead on record |
| Quality | `quality.detailed_message` | +10 | Description ≥ 120 characters |
| | `quality.vague_message` | 0 | Description < 15 characters (tracked, contributes nothing by default — change the weight if you want it to count) |

The total is clamped to 0–100. **Any city with no configured service area contributes no location signal at all** — a company that hasn't set up service areas yet is never penalized for it, per the spec's explicit instruction.

## Priority

`priority = "high"` if score ≥ `companies.lead_score_high_threshold` (default 80), `"medium"` if ≥ `lead_score_medium_threshold` (default 50), else `"low"`. Both thresholds are per-company and editable from the same settings section.

## Duplicate detection

`find_duplicate()` in `lead_intelligence.py`. Classifies into `exact` / `high_confidence` / `possible` / `none`:

- **exact** — the same phone and email both match one existing `CrmPerson`.
- **high_confidence** — phone alone matches a `CrmPerson`, or matches an existing `Customer`'s mobile/WhatsApp/email.
- **possible** — only the email matches a person, or the company name matches an existing `CrmOrganization`.
- **none** — nothing matches.

Phone comparison is done on a normalized 10-digit form (`normalize_phone`, strips +91/0 prefixes); email comparison is case-insensitive. **Nothing is ever auto-merged** — a match only sets `duplicate_status` and shows a banner on the lead; merging stays a manual, human decision (not built in this phase).

When scoring a lead that's already linked to a person, that person is excluded from their own match search — otherwise every linked lead would trivially show as a duplicate of itself. A pre-save check is also available at `GET /crm/leads/check-duplicate?phone=&email=&organization_name=`, for warning a user before they create a lead, not just after.

## Repeat-contact detection

Separate from duplicate detection on purpose: once a lead is correctly linked to an existing person, it's not a "duplicate" — but `find_repeat_contact()` still looks for that person's (or organization's) most recent *other* lead, and if found, surfaces its date, source, last known stage (from `crm_lead_stage_history`), status, and the salesperson who handled it. Available standalone at `GET /crm/leads/{id}/repeat-contact`, and as a `repeat.previous_enquiry` scoring signal.

## Normalized intake / source adapters

`NormalizedLeadInput` is the common shape any lead source produces before it reaches scoring (spec Step 2). Two adapters exist:

- `normalize_manual_lead()` — the shape leads created through the existing New Lead form already have.
- `normalize_indiamart_payload()` — **built against IndiaMART's commonly documented lead-push field names, not verified against a live account.** No IndiaMART integration exists in this deployment (confirmed during the audit — zero prior references anywhere in the codebase), so there's nothing to connect this to yet. It must be checked against real payloads before it's wired to an actual webhook.

`CrmLead.raw_source_data` keeps the original payload verbatim whenever a lead arrives through an adapter, so a broken integration stays debuggable from what was actually received.

## Known limitations, stated plainly

- **GST is only known post-conversion.** `CrmOrganization`/`CrmPerson` have no GST field, so `business.gst_available` can only fire once a lead has already converted to a `Customer`. Pre-conversion leads never get this signal, positive or negative — consistent with the spec's rule never to penalize GST's absence, but it means the signal is currently of limited use before conversion. Adding a GST field to `CrmOrganization` would close this; not done here, to keep this migration's schema change minimal — flagged for a future pass if it turns out to matter in practice.
- **Enquiry-type and message-quality signals are keyword/length heuristics**, not NLP. "Need 5000 pcs" and "price?" score very differently, as the spec's own examples intend, but a message that says the right thing in an unexpected way won't be recognized. This is deliberate (spec Step 23: deterministic first) — AI-assisted classification is a documented future option, not built here.
- **No IndiaMART credentials exist**, so that adapter is unverified against a live payload.

## Admin configuration

- **CRM Settings → Lead Scoring**: every rule's weight and active/inactive state, plus the two priority thresholds. Changes apply to future scoring (and anything re-scored); past scores keep their original breakdown and version.
- **Service areas**: `GET/POST/PATCH/DELETE /crm/service-areas` (API only in this phase — no dedicated settings UI yet).

## Future ML (not built, per spec Step 24)

The data model is shaped so that, once there's enough history, `CrmLead.score`/`score_breakdown`/`priority` alongside actual outcomes (`status`, conversion to `sales_order_id`, deal value) could train a model to check which signals actually predicted a real sale — but no ML runs today, and none should until there's real data to validate against.
