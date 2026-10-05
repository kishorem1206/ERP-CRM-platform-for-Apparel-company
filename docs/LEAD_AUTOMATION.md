# Lead Automation — Phase 2 Implementation

> Built 2026-10-05, on top of the real Phase 1 scoring/duplicate-detection engine (`docs/LEAD_SCORING.md`).
> Code: `backend/app/services/lead_assignment.py`, extensions to `backend/app/workers/tasks.py` and `backend/app/api/v1/endpoints/crm.py`.

## What already existed before this phase (reused, not rebuilt)

Before writing anything, the existing code was checked against the spec's 21 steps. Three pieces were already substantially built:

- **`_assign_lead`** (crm.py) — manual assignment already recorded history, notified the new assignee, created a "Make first contact" task, and fired a `lead_assigned` WhatsApp automation trigger. Phase 2 extends this function (a `task_due_at` parameter) rather than duplicating it — auto-assignment calls the exact same function a manual assignment does.
- **`flag_missed_followups`** (Celery, hourly) — already auto-creates a high-priority task, sends an in-app notification, and fires a `follow_up_due` WhatsApp trigger for any scheduled follow-up that's lapsed, idempotently (skips leads that already have an open task from this source). This covers most of spec Steps 6–7 for the "already-scheduled-but-missed" case.
- **The WhatsApp automation engine** (`whatsapp_automation.py`, documented in the Phase 1 audit) — 5 trigger points, templated messages, delayed dispatch, per-send logging. Nothing here needed changing; `lead_assigned` already fires through `_assign_lead`.

## What's new

### Smart assignment (Steps 1–2)

`lead_assignment.py`:
- **Rule-based** — `crm_lead_assignment_rules`, ordered by `sort_order`. First active rule whose conditions (source / minimum score / location tier — each optional, AND'd together) all match gets the lead. Configured in CRM Settings → Lead Assignment.
- **Round-robin fallback** — `crm_lead_assignment_pool` (active employee list) + `crm_round_robin_state` (one row per company, remembers who got the last lead). No rule match → next person in the pool, in order, wrapping around.
- Manual assignment (pre-existing) is untouched and always wins — auto-assignment only runs in `POST /crm/leads` when nobody supplied `assigned_to`.

**Scoping note on "Team A" from the spec:** this codebase has no Team/group entity (confirmed in the Phase 1 audit). A rule's action assigns to one specific employee, not a team. Building Teams was out of scope for this phase.

### Priority-based response targets (Step 3)

`companies.response_target_high_minutes` (default 30) / `_medium_hours` (24) / `_low_hours` (72) — configurable. On auto-assignment, `CrmLead.response_target_at` is set from whichever applies to the lead's priority, and the auto-created "Make first contact" task is due at that same time (instead of always 24h later) with `high` priority when the lead is high-priority.

### Response-time tracking (Step 9)

- `CrmLead.first_contacted_at` — set once, the first time an activity is marked done against the lead (distinct from the pre-existing `last_contacted_at`, which updates on every contact).
- `time_to_assignment_minutes` / `time_to_first_response_minutes` — computed on the fly in the lead detail response, not stored (so there's nothing to keep in sync).
- `GET /crm/reports/response-time` — company-wide average/median for both metrics, a high-priority-only cut, and a per-employee breakdown. Only counts leads that actually have the relevant timestamps; an untouched lead isn't silently counted as zero.

### Overdue escalation (Step 8)

New Celery task `escalate_uncontacted_high_priority_leads`, every 30 minutes. Two stages, each gated by its own notified-at timestamp so a lead is never re-notified for the same stage:

1. `response_target_at + escalation_employee_hours` (default 2h) past and still no `first_contacted_at` → notify the assigned employee. Sets `escalation_employee_notified_at`.
2. `response_target_at + escalation_manager_hours` (default 4h) past, still uncontacted → notify every active owner (`users.is_owner`) on the company. Sets `escalation_manager_notified_at`.

Distinct from `flag_missed_followups`: that task is about a *scheduled* follow-up that lapsed; this one is about a lead that's never been contacted at all since assignment.

### Employee "My Work" (Step 4)

New page, `/crm/my-work`. Five live sections, each clickable through to the lead or task: High Priority — Not Yet Contacted, Overdue Follow-ups, Follow-ups Due Today, My Pending Tasks, New Leads (last 24h). All scoped to the signed-in employee — "the employee's first screen," per the spec's own framing.

### Manager visibility (Step 20, partial)

A company-wide "🔥 N high-priority leads have not been contacted yet" banner was added to the existing CRM Dashboard, linking to My Work. A dedicated, separate Manager Dashboard page (workload-per-employee, platform performance, ad-spend ROAS) was **not** built this round — see Deferred below.

## Admin configuration

CRM Settings → **Lead Assignment**: rules (create/toggle/delete), round-robin pool (add/remove employees), response targets, and escalation hours — all in one section, all admin.settings-gated.

## Verification

Full functional chain tested against real data: lead created with no explicit assignee → scored → rule-based assignment correctly took priority over round-robin when a matching rule existed → round-robin correctly rotated → "Make first contact" task auto-created with the right due date and priority → `response_target_at` computed correctly from company settings → response-time report returned real (non-fabricated) aggregates from existing historical leads → escalation task run directly, correctly found a backdated high-priority uncontacted lead, notified, and set its idempotency timestamp (confirmed a second run would skip it).

One real bug found and fixed during this verification: `ResponseTargetsOut` (and, found alongside it, `ScoringThresholdsOut`) was missing `model_config = {"from_attributes": True}`, so validating it from the `Company` ORM object raised a 500. Both fixed; re-verified with a full GET → PUT → restore round trip.

24-endpoint regression sweep (everything touched across both phases): 24/24 healthy.

`tsc --noEmit` and `npm run build` pass. Both containers rebuilt.

## Deferred — not built this round

Stated plainly, matching how Phase 1's scope was reported:

- **Catalogue automation beyond the existing trigger** (Step 12) — `catalogue_shared` already fires a WhatsApp message; it doesn't yet auto-create a follow-up task the way `lead_assignment` and `missed_follow_up` do. Same for `quotation_generated` and `sample_dispatched`.
- **Structured follow-up outcome picker** (Step 13) — the outcome field on "Complete Activity" is still free text, not the spec's fixed set (Interested / Not Interested / Price Issue / etc.) with an auto-suggested next action per outcome.
- **Employee workload view** (Step 14) — a per-employee breakdown (assigned leads, high priority, pending follow-ups, overdue, conversions) for managers. Data exists (response-time report shows the shape); no dedicated view.
- **Platform / ad-spend quality reporting** (Steps 15–16) — ad-spend data and CPL/CPA/ROAS already existed before this phase; a score-quality breakdown by platform was not added.
- **Sales activity timeline** (Step 17) — a unified chronological view (stage changes + activities + tasks + automation log in one list) was not built; the data exists across `crm_lead_stage_history`, `crm_activities`, `crm_tasks`, and `whatsapp_automation_logs` separately.
- **Pre-due reminders** (Step 7's "30 minutes before") — only the after-due-time reminder (`flag_missed_followups`) and the new after-target escalation exist. Nothing fires before a follow-up's scheduled time.
- **A dedicated Manager Dashboard page** — only the one banner on the existing CRM Dashboard.
