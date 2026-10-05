# Predictive Scoring — Data Readiness Audit

> Run 2026-10-05 against the real company (`cfa4e79d-ddd7-4c04-8432-d690a97d1b84`), live database. Every number below is a direct query result, not an estimate.
> This is Phase 1 of the Predictive Scoring spec: "Determine whether there is enough data to train a meaningful model. If there is not enough data: BUILD THE DATA FOUNDATION. Do not fabricate model accuracy."

## Headline numbers

| Metric | Value |
|---|---|
| Total leads | **9** |
| Status: open | 7 |
| Status: won | 1 |
| Status: lost | 1 |
| Leads with `sales_order_id` set (lead → order link) | **0** |
| Date range | 2026-08-08 to 2026-09-06 (29 days) |
| Leads with `first_contacted_at` set | 0 |
| Leads with a computed `score` | 0 |
| Rows in `crm_lead_stage_history` | 0 |

## Conclusion, stated first

**There is nowhere near enough data to train any predictive model, by a wide margin.** This isn't a judgment call — the numbers make it unambiguous:

- A prediction target needs **both** a meaningful count of positive outcomes (converted) and negative outcomes (didn't) to learn from. There is **1 of each**. A model "trained" on 1 won and 1 lost lead doesn't learn a pattern — it memorizes two specific rows and will confidently overfit to noise.
- Even the simplest interpretable model the spec recommends starting with (logistic regression) needs, as a standard rule of thumb, on the order of 10–20 labeled outcomes *per feature* to avoid severe overfitting. The feature set this spec itself proposes — quantity, source, location, contact validity, business signals, message quality, and more — is a dozen-plus features. That alone implies wanting **150–300+ labeled outcomes at minimum**, not 2.
- **No lead in the database is linked to the order it produced.** `sales_order_id` is 0-for-9. Conversion can't currently be measured reliably even for the few leads that exist — see Data Quality below.
- There are 0 rows of stage history across all 9 leads, meaning none of them has ever recorded moving through the pipeline. There's no "journey" data to learn from yet, only a snapshot.
- All 9 leads were created in a single 29-day window — not enough calendar time for the spec's own required chronological train/validation/test split (Phase 8) to produce anything but near-empty splits.

**Per the spec's own instruction, no model is being built.** Everything below documents the gap precisely and what closing it actually requires, rather than a model trained on data this thin.

## Full breakdown

### Leads

| Dimension | Breakdown |
|---|---|
| By source | IndiaMart: 5, Referral: 1, (none): 3 |
| By priority | (unscored): 9 — see Data Quality |
| By assignee | System Administrator: 8, kishore: 1 |
| By status | open: 7, won: 1, lost: 1 |

Leads by month, by platform-beyond-source, by product, and by location were not separately tabulated — with 9 total rows, slicing them any further than the above produces tables of 0s and 1s, not signal. Re-run this audit's queries (kept below) once volume justifies finer breakdowns.

### Conversion

- Total converted (status = won): 1 (11% of 9 — **not a usable conversion rate**, it's one data point)
- Conversion by source / employee / product / score / location: not computed. With 1 positive example total, any breakdown by dimension is reporting where that single data point happens to fall, not a rate.

### Sales

- Quotations (CRM): 3 total, 0 accepted
- Sales orders (company-wide, ERP side): 10
- Customers (company-wide): 12, of which 4 have placed more than one order
- **These 10 orders and 12 customers are not reliably traceable back to CRM leads** — only the `sales_order_id` link on `crm_leads` could connect them, and it's null on all 9. Either these orders were created directly through the Sales module (bypassing the CRM lead flow — plausible, since the ERP existed before the CRM module was added this project cycle) or the link simply isn't being set anywhere yet. Either way, "which leads produced these orders" cannot currently be answered from the data, which is itself the most important gap for Target 1 (probability of conversion) and Target 3 (expected order value).

### Activity

- `crm_activities`: 11 total (company-wide, not lead-specific — includes activities with no `lead_id`)
- `crm_tasks`: 10 total
- Leads with `first_contacted_at` set: 0 — this field was only added today (Phase 2) and isn't backfilled, so even the 9 existing leads have no recorded first-contact time yet. Response-time-to-conversion correlation (spec Phase 14) has zero rows to work from today.
- Leads with any linked product (`crm_lead_products`): 2 of 9

### Data quality

- **3 of 9 leads have no `organization_id`** — a fifth of the already-tiny dataset, further thinning any business-identified signal.
- **0 of 9 leads have a computed `score`** — expected: Phase 1's `score_lead` runs only on lead *creation*, and these 9 leads predate that code existing. There's no retroactive backfill. This means the rule-based score (the baseline the spec says a predictive model must be compared against — Phase 25) doesn't even exist yet for the historical leads that would otherwise form a training set.
- **0 rows of stage history** for any of the 9 leads, despite the feature existing and being written on every stage change going forward (confirmed working in Phase 1/2 testing). The historical leads simply never moved stages after that tracking went live, or moved before it existed.
- No duplicate-lead or incorrect-date issues were found in this count — there isn't enough volume for duplicates to likely exist yet.

## What "build the data foundation" means concretely here

Not a model. Three things, in order of how directly they unblock future prediction:

1. **Link leads to the orders they produce.** `crm_leads.sales_order_id` exists and is set on conversion (confirmed in the Phase 1 model) — but 0 of the 9 historical leads have it. Check why: were these 9 converted through a path that doesn't set it, or do they simply predate the field? Going forward, every order that originated from a CRM lead needs this link, or "conversion" can never be measured from data, model or no model.
2. **Let the system run for real.** Volume is the actual blocker, and there's no shortcut around that — the data has to come from real enquiries over real time. The chronological split the spec requires (Phase 8) needs months of history, not weeks.
3. **Re-run this audit periodically** (suggest: monthly, or triggered by lead count) rather than guessing when it's "enough." The thresholds below make that check mechanical, not a judgment call each time.

## Data sufficiency gate (the one piece built today)

Per spec Phase 30 — the system should be able to say "predictive scoring unavailable: insufficient historical data" with real numbers, rather than staying silent or, worse, showing a score that isn't real. A live readiness check was built: `GET /crm/predictive-scoring/readiness` (see `docs/PREDICTIVE_SCORING_ARCHITECTURE.md`). Today it reports:

```
ready: false
leads_total: 9           (gate: 200)
converted: 1              (gate: 30)
not_converted: 1          (gate: 30)
reason: "9 of 9 leads needed overall; 1 of 30 converted outcomes; 1 of 30 non-converted outcomes"
```

The thresholds (200 total / 30 of each outcome) are a starting point, not a scientifically derived minimum — documented as such in the architecture doc, and configurable without a code change once there's a real basis to tune them.

## Next step

Nothing further on predictive scoring until the gate above reports `ready: true` on real data. Re-run the queries in this audit (or just call the readiness endpoint) periodically rather than resuming this spec on a timer.


## Update — 2026-10-05, same day

Two things done after the initial audit, per request:

1. **Found and fixed a real gap the audit surfaced**: `sales_order_id` was correctly set on lead conversion (confirmed in `convert_lead_to_sales_order`) but was never exposed through `GET /crm/leads` or `GET /crm/leads/{id}` — so nothing downstream, no report, no UI, could actually see the lead-to-order link even where it existed. Added to `LeadOut`/`LeadListOut`.
2. **Created 2 new dummy leads** (clearly marked `[DEMO]` in their titles) to verify the fix end-to-end: one converted through the real `/convert` endpoint (confirmed `sales_order_id` now correctly appears in the API response), one marked lost for symmetry.

Updated real numbers: **11 total leads** (was 9), 2 won (was 1), 2 lost (was 1), **1 lead now genuinely linked to its order** (was 0).

**This does not change the conclusion.** The readiness check still correctly reports `ready: false` — 11 of 200 required, 2 of 30 converted, 2 of 30 non-converted. Two demo leads added to verify a fix is not a path to predictive-scoring readiness, and nothing here was done to make the gate report differently than reality.
