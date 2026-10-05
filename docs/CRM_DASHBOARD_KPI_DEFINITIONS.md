# CRM Dashboard — Sales KPI Definitions

Backend: `backend/app/services/crm_kpi.py`. Endpoint: `GET /crm/reports/sales-kpis`.
Drill-down: `GET /crm/leads` with `kpi`, `created_from`, `created_to`, `utc_offset_minutes` (same definitions).
Tests: `backend/tests/test_crm_kpi.py`.

## Cohort rule (applies to every KPI)

The selected period defines the **lead cohort**: leads whose `created_at` falls inside the period.
Outcomes are then read for those leads, with no date limit. A lead created in September and won in October
counts as won in the September cohort.

Period boundaries are the browser's local calendar days. The browser sends `utc_offset_minutes`
(`-new Date().getTimezoneOffset()`), so "1 Sep" means 1 Sep in the user's timezone.

Filters that narrow the cohort: pipeline, employee (`assigned_to`), lead source (`source_id`). Campaign and
product filters are not implemented; the lead model has no campaign field and products are not stored on the lead.

## KPIs

| KPI | Definition | Formula | Included | Excluded |
|---|---|---|---|---|
| New Leads | Count of cohort leads | `COUNT(cohort)` | Every lead with `created_at` in the period | Activities, tasks, opportunities |
| Qualified Leads | Cohort leads that ever reached the pipeline's qualification stage or any later stage, or were won | `COUNT(qualified)` | See "Qualified" below | Leads whose pipeline has no qualification stage set |
| Lead → Qualified | Qualified ÷ New × 100 | rate, 1 dp | — | Shows `—` when New = 0 |
| Won Deals | Cohort leads with `status = 'won'` | `COUNT(won)` | Won at any later date | Won leads created outside the period |
| Lead → Won | Won ÷ New × 100 | rate, 1 dp | — | Shows `—` when New = 0 |
| Avg. Time to Close | Mean of `closed_at − created_at` over cohort leads that are won | days, 1 dp | Won leads with a `closed_at` on or after `created_at` | Won leads without `closed_at`; negative durations |

### Qualified

A lead is qualified when any of these hold:

1. Its current stage is in the pipeline's qualification stage or later, and the stage is not lost.
2. It has a stage-history row to a stage at or after the qualification stage, in the same pipeline, that is not lost. This is the case when a lead was qualified and later moved back or lost.
3. Its status is `won`. A won deal necessarily passed qualification, even if the CRM stage was never moved.

The qualification stage is `crm_pipelines.qualified_stage_id`, set per pipeline in CRM Settings → Qualification Stage. Reporting never matches on a stage name.

Known limit: a lead lost with no stage history and a lost current stage is not qualified, because nothing shows it ever reached qualification. Leads created before stage history was recorded are judged by their current stage only.

### Won

Won uses the lead's `status`, set by the status endpoint and by the convert-to-order flow. The stage's `is_won` flag is not used.

## Previous-period comparison

- A full calendar month, quarter or year selection is compared with the previous calendar month, quarter or year.
- Any other selection is compared with the immediately preceding period of the same length.

Each previous-period value uses the same cohort and outcome rules, with the outcomes read as of now.

Comparison display:

- Counts (New, Qualified, Won): relative change `(current − previous) ÷ previous × 100`. If previous = 0 the card shows `New` (when current > 0) or `—`.
- Rates (Lead → Qualified, Lead → Won): percentage-point change.
- Avg. Time to Close: absolute day change. A decrease is shown as good, an increase as bad.

## Edge cases

- No leads: all counts 0; rates and average time are `null` and display `—`.
- Zero denominator: rates return `null`, never NaN or Infinity.
- No previous records: relative change returns `null`.
- No won deals with a close time: average time is `null`; the card states how many won deals it is based on.
- Missing `closed_at` on a won lead: counted as won, excluded from the time average.
- `closed_at` before `created_at`: excluded from the time average.
- Lead moved backward or reopened: qualification uses history, so it is kept.
- Lead skipped stages: counted as qualified if the stage it reached is at or after the qualification stage.
- Lead qualified then lost: counted as qualified, not won.
- Multiple opportunities for one contact: each lead is counted separately; leads are the unit of the cohort.
- Leads in a pipeline with no qualification stage set: they cannot be counted as qualified. The API returns `leads_in_pipelines_without_qualification_stage`, and the dashboard shows a warning.
- Leads with no pipeline: same as the previous case.

## Known data state (2026-10-05)

- Twelve pipelines named "Sales Pipeline" are all marked default; eleven have no stages. The kanban and the dashboard select the default pipeline that has stages, earliest created first. The duplicates should be removed; that is a data action not yet taken.
- One won lead in the previous period has no `closed_at`, so the time average for that period is `—`.
- The "Won" stage holds ₹300.00 Cr, which looks like a data-entry outlier. It is not corrected here.

---

# Current Open Pipeline

Backend: `backend/app/services/crm_kpi.py` (`load_open_pipeline`, `compute_open_pipeline`). Endpoint:
`GET /crm/reports/open-pipeline`. Drill-down: `GET /crm/leads?kpi=open` and `?kpi=aged`, optionally with `stage_id`.
This section is a current-state snapshot. The dashboard period does not apply to it.

## Open opportunity (current)

A lead is an open qualified opportunity when all of these hold:

1. `status = 'open'`.
2. Its current stage is not terminal (`is_won` and `is_lost` are both false).
3. It has qualified, using the same rule as the Core KPIs: it was won, or it has reached the pipeline's qualification stage or later, now or in its stage history.

No creation-date filter applies. A lead created a year ago counts if it is still open and qualified.

Excluded: won, lost, and leads whose status is open but whose stage is Won or Lost. The last case is shown as a data warning, because the status and stage disagree and someone has to decide which is right. "Cancelled" does not exist in the model, so it is not excluded.

## Open pipeline value

Sum of `lead_value` over the open opportunities above. This is expected value of open deals, not revenue, and it is never derived from orders or invoices. It uses the current value only, because value changes are not recorded in history.

## Stage split

Open opportunities grouped by their current stage, with count and value. Stage counts sum to the open count by construction.

## Older than 30 days

Open opportunities whose `created_at` is more than 30 days before now. This is a subset of the open count. It uses the lead's creation time, which is the record's own creation time, so it is also the opportunity's age.

## Comparison point (previous snapshot)

The reference date is the last day of the previous calendar month, in the browser's local timezone. The previous snapshot is the same open-qualified rule applied as of the end of that day.

A past snapshot can only be rebuilt from stage history. Stage history records every stage change from the day it was introduced. Before that, the state at a past date is unknown. So the comparison is shown as available only when the reference date is on or after the first recorded stage change. Otherwise the card shows `—` and states why. This is the current situation: no stage changes have been recorded yet, so the comparison is unavailable.

Limits on the reconstruction:

- A lead that was reopened keeps its first close time. Its past open state is approximate for the time between reopening and now. The number of reopened leads is returned as `data_notes.reopened_count`.
- A lead with a closed status but no close time has an unknown close date, so it is excluded from any past snapshot. Returned as `won_lost_without_close_date`.

## Movement since the reference date

Movement is a bridge between the two snapshots:

- `added` ("new"): open-qualified now, not open-qualified at the reference date. This includes new leads and leads that qualified after the reference date.
- `won`: open-qualified at the reference date and won since it, with the close time in the window.
- `lost`: open-qualified at the reference date and lost since it, with the close time in the window.
- `other`: anything else that left the set. The bridge is checked, and `movement.reconciles` must be true:

  previous + added − won − lost − other = current

Movement is not shown when the previous snapshot is unavailable.

## Edge cases

- No open opportunities: count 0, empty stage list.
- No previous snapshot: comparison and movement are `null`; the UI shows `—`.
- Lead with no qualification stage configured on its pipeline: not qualified unless won. Counted in `data_notes.open_without_qualification_stage`.
- Leads without a pipeline: not qualified unless won.
- Reopened and moved-backward leads: handled as described above; qualification follows history.

## Verified with real data (2026-10-05)

- Endpoint open count, the drill-down list for `kpi=open`, and the stage counts all return 4.
- The aged set returns 4, the same as the endpoint's `older_than_30_days_count`.
- One lead with status open and stage Won (lead value ₹300.00 Cr) is excluded and disclosed.
