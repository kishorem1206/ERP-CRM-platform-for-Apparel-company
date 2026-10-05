# Lead Intelligence Audit — Phase 1 (Step 1 of the Lead Intelligence spec)

> Created: 2026-10-05
> Scope: Step 1 only — inspect the existing system, document findings, propose a phased plan. No schema or code changes in this document.
> This is a **different initiative** from `docs/proleeds prompt.md` / `docs/PROLEEDS_FEATURE_AUDIT.md` — see "Relationship to the Proleeds audit" below before reading further, so the two don't get confused.

---

## Relationship to the Proleeds audit

Before starting this audit, `docs/PROLEEDS_FEATURE_AUDIT.md` (dated 2026-09-03) was checked for overlap, since it already catalogues the CRM's pipeline, lead, and contact architecture in detail.

**Finding: no overlap on the core ask.** The Proleeds audit covers dashboards, configurable pipelines, workflow automation, tasks/workspaces, unified inbox, and 14 other areas — it never mentions lead scoring, signal extraction, or duplicate detection. Those are genuinely new concerns this document is the first to address.

**Two things worth knowing, though:**
1. The Proleeds audit already recommended adding a `temperature` field to `CrmLead` (its row C7, status `MISSING`). That field **now exists** (`temperature: Mapped[str]`, default `"cold"`) — implemented since that audit was written, as part of a separate "CRM Phases 1-8" commit. The Proleeds audit is stale on that one point; nothing else in it was re-verified here.
2. This repo has used "Phase N" in at least three unrelated numbering schemes already: `docs/ERP_UPGRADE_PROGRESS.md`'s workflow-shell phases, the "CRM Phases 1-8" git commit, and the Proleeds audit's own Phase 1–18 roadmap. The Lead Intelligence spec's "PHASE 1" is a **fourth**, separate scheme. None of these align by number — treat each document's phase numbers as scoped to that document only.

---

## 1. Lead model (`CrmLead`, table `crm_leads`)

Already has: `title`, `description`, `lead_value`, `temperature` (cold/warm/hot), `status` (open/won/lost), `lost_reason`, `expected_close_date`, `pipeline_id`, `stage_id`, `source_id`, `type_id`, `person_id`, `organization_id`, `customer_id`, `assigned_to` (+ assignment audit fields), `next_follow_up_at`/`follow_up_type`/`follow_up_reason`/`follow_up_notes`/`follow_up_status`, `last_contacted_at`, `contact_outcome`, `next_action`, `sales_order_id` (set on conversion), `created_by`, timestamps.

**Does not exist, and the spec needs it:** `source_lead_id` (the external platform's own lead ID), `received_at` (distinct from `created_at`, for when the platform says the enquiry happened vs when we ingested it), `raw_source_data` (original payload, for debugging integration problems), `normalized_data`, any quantity/product/GST/phone/city fields (those live on `CrmPerson`/`CrmOrganization`/`Customer`, not on the lead itself — see below), and nothing resembling a score, priority, or signal breakdown.

**No separate Opportunity model.** `CrmLead` *is* the opportunity record — it carries `lead_value`, `pipeline_id`, `stage_id` directly. The spec's "Opportunity model" checklist item maps onto this.

## 2. Customer, Contact, Company models

- **`CrmPerson`** (table `crm_persons`) — the pre-sale contact: `name`, `job_title`, `city`, `emails` (JSONB array of `{value,label}`), `contact_numbers` (same shape), `whatsapp_number`, `organization_id`, `customer_id` (optional link once converted), `assigned_to`.
- **`CrmOrganization`** (table `crm_organizations`) — `name`, `website`, `address` (JSONB), `assigned_to`. No GST field here.
- **`Customer`** (table `customers`, in the sales/ERP side, not CRM) — the real buyer account, created on lead conversion. Has `gstin`, `pan`, `mobile`, `whatsapp_no`, `email`, `location`, `customer_type` (domestic/export), credit terms, price list, sales person. **GST lives here, not on the CRM contact** — a lead has no GST until it converts to a customer, unless a new field is added to `CrmOrganization`/`CrmPerson` for pre-conversion GST capture (the spec explicitly expects GST as a possible lead-time signal).
- **`Company`** — the tenant (your business), unrelated to the buyer's company name. Not to be confused with `CrmOrganization`.
- **User/Employee** — `User` + `Role`/`Permission`/`RolePermission`/`UserRole`, already extensively used (permission-gated UI was built earlier this session). No separate "Employee" concept.

**No quantity, product-category, fabric, GSM, colour, size, composition, customization, delivery-requirement, or target-price fields anywhere in CRM.** The closest existing structure is `CrmLeadProduct` (lead ↔ `Product`/`ProductVariant` link with `quantity_interested` and free-text `notes`) and the free-text `description` on `CrmLead` — neither is structured enough for the signal extraction the spec wants (Step 4–5). This is the single largest structural gap for scoring.

## 3. Lead source / Opportunity / Pipeline / Pipeline stages

- **`CrmLeadSource`** (table `crm_lead_sources`) — just `{id, company_id, name, created_at}`. A flat, admin-managed label list (e.g. a company could already have added a row named "IndiaMART" by hand), with **no structured platform/adapter concept, no external credentials, no per-source configuration.** This is the field the spec's "source/platform" maps onto today, but it has none of the adapter architecture Step 3 describes.
- **`CrmLeadType`** — same shape, same limitation, used for a different classification axis (not source).
- **`CrmPipeline`** / **`CrmPipelineStage`** — fully configurable, already confirmed working this session (the "No pipeline stages configured" bug fixed earlier today was a frontend data-shape bug, not a backend limitation). Stages have `name`, `code`, `color`, `probability`, `sort_order`, `is_won`, `is_lost`. One pipeline currently exists per company ("Sales Pipeline", 6 stages), but the model supports more.
- **Correction to an earlier version of this document:** a `CrmLeadStageHistory` table does exist (`crm_lead_stage_history`), is written on every stage change, and is exposed via `GET /crm/leads/{id}/stage-history` — confirmed while wiring the scoring engine below. This directly helps repeat-contact detection (Step 11): "previous lead status" and the stage journey are both already queryable.

## 4. Activities, Follow-ups, Tasks

- **`CrmActivity`** (table `crm_activities`) — generic interaction log: `title`, `type` (free text — "Call", "Meeting", "Phone Call", "Sample Sent", etc., not an enum; the `/crm/follow-up-types` admin list defines the current options, but the column has no constraint, and legacy rows store lowercase variants of the same names — found and left alone during an unrelated fix earlier today), `comment`, `is_done`, `schedule_from`/`schedule_to`, `lead_id`, `person_id`, `assigned_to`.
- **"Follow-up"** is not a separate entity. It's partly fields directly on `CrmLead` (`next_follow_up_at` etc.) and partly just `CrmActivity` rows. There is no dedicated FollowUp table the spec's Step 11 ("previous enquiry date... previous outcome") can query in one place — that information is scattered across `CrmActivity`, the lead's own follow-up fields, and (after conversion) `SalesOrder`/quotation records.
- **`CrmTask`** (table `crm_tasks`) — separate from Activity: `title`, `notes`, `lead_id`, `customer_id`, `assigned_to`, `due_at`, `priority`, `status`, `source`.

## 5. Notifications

`Notification` model + `create_notification`/`publish_notification` (Redis pub/sub) in `app/services/notification.py` — generic, already used by several modules. A Lead Intelligence "high-score lead went untouched" alert (spec Step 25) would reuse this, not need a new mechanism.

## 6. Existing integrations / IndiaMART / webhook architecture

**No IndiaMART integration exists anywhere in this codebase** — confirmed with a full-repo search, zero references. There is also no credentials/config field reserved for it anywhere in `app/core/config.py`.

**The only existing inbound webhook is WhatsApp's** (`GET/POST /api/v1/whatsapp/webhook`), and it's the closest template for how Step 3's `LeadSourceAdapter` → webhook layer should be shaped here: a `GET` handler for the provider's verification handshake, a `POST` handler that enqueues processing as a background task and returns immediately, and a `_process_inbound_*` function that does the actual normalize-and-store work inside its own DB session.

**One thing worth not copying:** that webhook resolves which company owns an inbound message with `select(Company).limit(1)` — it picks an arbitrary first company, not the one the WhatsApp number actually belongs to. That's a pre-existing single-tenant assumption baked into the only prior art available. An IndiaMART (or any) adapter needs real company resolution — e.g. a per-company webhook URL or API key — and should not inherit this shortcut.

## 7. Existing search/filter architecture

Organizations, Persons, and Products list endpoints all accept a `search` query param (`ILIKE` on name). **The Leads list endpoint (`GET /crm/leads`) does not** — it only supports `stage_id`, `status`, `assigned_to`, `follow_up_due`. The frontend's lead search box sends a `search` param anyway; FastAPI silently ignores unrecognized query params, so **the Leads search box has never actually filtered anything.** This is an existing bug, unrelated to today's two fixes, found while checking this item for the audit. Not fixed here, since the plan was audit-only — flagging it because Step 19 of the Lead Intelligence spec explicitly wants search as a filter dimension, and it would be natural to fix alongside that work rather than separately.

## 8. Existing permissions/RBAC

Role → Permission → RolePermission → UserRole, already used throughout CRM (`crm.view`/`create`/`edit`/`delete`/`assign`). An admin-configurable scoring-rules area (Step 22) would sit naturally behind a new permission (e.g. `crm.admin` or reusing `admin.settings`), consistent with how Company Settings already works.

---

## Summary: what Step 1's checklist found

| Spec concept | Status |
|---|---|
| Lead model | EXISTS, is the Opportunity too, missing source/signal/score fields |
| Customer/Contact/Company models | EXIST, split across `CrmPerson`/`CrmOrganization`/`Customer`/`Company` as described above |
| Lead source | EXISTS as a flat label list only — no adapter/platform architecture |
| Opportunity model | Does not exist separately — folded into `CrmLead` |
| Pipeline / stages | EXISTS and fully configurable, including stage history |
| Activities / Tasks | EXIST; "Follow-up" is not its own entity |
| Notifications | EXISTS, generic, reusable |
| IndiaMART integration | Does not exist |
| Webhook architecture | One precedent (WhatsApp), with a single-tenant shortcut not to repeat |
| Search/filter architecture | Inconsistent — most lists have it, Leads list's `search` param is a no-op bug |
| Permissions/RBAC | EXISTS, mature, easy to extend |
| Duplicate detection | Does not exist anywhere in the codebase |
| Phone/email normalization | Does not exist — even the one existing "dedup" (WhatsApp contacts) matches on exact string, no normalization |
| Lead scoring / signals / priority | Does not exist |

**The single largest gap**, more than any missing table: there is nowhere today that a quantity, product spec, GSM, or target price from an enquiry message gets captured as structured data. Everything stronger than `lead_value` (a single number) and `description` (free text) would need new fields or a new signal-extraction step working off that free text.

---

## Proposed phased plan (for your review — nothing below has been built)

Numbered independently from every other "Phase" scheme in this repo.

1. **Normalized lead intake fields** — add `source_lead_id`, `received_at`, `raw_source_data`, `normalized_data` (plus the structured requirement fields: quantity, product category, target price, etc.) to `CrmLead`, additive migration only.
2. **Lead source adapter interface** — formalize `CrmLeadSource` into something an adapter can target; build the `LeadSourceAdapter` interface and a `ManualLeadAdapter` + fixture-based `IndiaMARTAdapter` (no real IndiaMART credentials exist yet, so it's built and tested against mock payloads, clearly documented as needing real credentials before going live).
3. **Signal extraction layer** — deterministic rules reading the normalized lead (requirement specificity, quantity, enquiry type, location, contact validity, business-vs-individual, message quality), each signal independently testable.
4. **Duplicate + repeat-contact detection** — phone/email normalization utility (doesn't exist yet), match tiers (exact/high-confidence/possible/none) against `CrmPerson`/`CrmOrganization`/`Customer`, surfaced on the lead before scoring runs.
5. **Scoring engine** — configurable weights/thresholds (stored in config, not code), score breakdown persisted per lead with a scoring version, Priority derived from configurable thresholds.
6. **UI** — score + priority on the lead card and kanban, a "Lead Intelligence" section on lead detail with the full breakdown, admin configuration screen for rules/weights/thresholds, the Leads list search-bug fix and the new filter dimensions (priority, score range, source, duplicate status) together.
7. **Reporting** — score-band conversion rates, duplicate rate, source performance, once there's enough scored-lead data for it to mean anything.

Steps 1–3 can proceed without touching anything the rest of the CRM depends on. Step 4 (duplicate detection) is worth building early since the repeat-contact signal is explicitly called out as high-value and touches the fewest other systems. Step 2's real IndiaMART connection is blocked on credentials that don't exist yet — the adapter and its tests can be built now regardless.
