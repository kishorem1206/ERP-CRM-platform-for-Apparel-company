# Predictive Scoring — Architecture

> 2026-10-05. Documents what exists today (the data-sufficiency gate) and the planned architecture for when there's enough data to build on — not a model that's been built.
>
> The spec this phase is based on also asks for `PREDICTIVE_SCORING_MODEL.md` and `PREDICTIVE_SCORING_OPERATIONS.md` — documenting training process, model version, calibration, retraining. Those aren't written yet, deliberately: there's no model, so there's nothing true to put in them. Writing them now would mean documenting a process that doesn't exist, which is the same "fabricate accuracy" problem the spec itself warns against, just in doc form instead of code. They get written when a real model exists to describe.

## What exists today: the readiness gate

`GET /crm/predictive-scoring/readiness` (`backend/app/api/v1/endpoints/crm.py`). Compares three live counts against two company-configurable thresholds (`companies.predictive_scoring_min_leads`, default 200; `predictive_scoring_min_outcomes_per_class`, default 30):

```
ready = (
    leads_total >= min_leads
    AND converted >= min_outcomes_per_class
    AND not_converted >= min_outcomes_per_class
)
```

"Converted" currently reads `CrmLead.status == 'won'`. The data audit found this is the only usable signal today — `sales_order_id` (the more rigorous order-linked definition the spec prefers, Phase 3) is unset on every existing lead. This is flagged in the audit as a gap worth closing regardless of predictive scoring, since it also affects every other order-attribution report in the CRM.

Surfaced in CRM Settings as a plain status card — real numbers, no prediction, explicitly labeled "Not Available Yet."

## Why 200 / 30 / 30, and why that's not precise

Stated in the audit doc as a starting point, not a derived minimum: it's in the right order of magnitude for a simple logistic-regression-class model with a double-digit feature count (the standard "10-20 observations per feature" heuristic, applied to a feature set this size), not a number computed from this business's actual variance. These are company-level columns specifically so they can be revised once there's a real basis to tune them — e.g., after the first model is actually trained and its learning curve shows where performance plateaus.

## Planned architecture (not built — for when the gate opens)

Kept here as the reference plan so building it later doesn't mean re-deriving the shape from scratch, and so the eventual implementation doesn't drift from what was already thought through.

```
CRM (leads, activities, orders)
        │
        ▼
Feature extraction  — a dedicated service, reading only PREDICTION POINT A
        │              features (spec Phase 5): what's known at lead
        │              creation, nothing from after. A point B and C
        │              extractor come later, separately, once point A
        │              is validated — predicting with future information
        │              is the single most important failure mode to
        │              design out from the start.
        ▼
Model training — offline, reproducible script (not a notebook), chronological
        │          split (spec Phase 8), evaluated on precision/recall/
        │          ROC-AUC/calibration (Phase 9-10), never on accuracy alone
        ▼
Model registry — versioned (spec Phase 21): every prediction stores which
        │          model version produced it, so a score stays traceable
        │          even after the model is retrained
        ▼
Prediction service — called from the backend only (spec Phase 28 — the
        │              frontend is never responsible for predicting
        │              anything), falls back to the existing rule-based
        │              score if the model is unavailable or data for a
        │              specific lead is incomplete (spec Phase 29 —
        │              the CRM must keep working either way)
        ▼
CRM — shows BOTH scores side by side (rule-based, already live; predictive,
       once it exists), never one replacing the other until the predictive
       side has a measured track record (spec Phase 25, champion/challenger)
```

Key design decisions already settled, so they're consistent whenever this gets built:

- **Rule-based score and predictive score stay side by side, permanently**, not one replacing the other — the existing `CrmLead.score`/`priority` columns (Phase 1) are the "rule score" lane; a predictive score would live in new, separate columns, never overwriting them.
- **Prediction Point A only, first.** Everything knowable at the moment a lead is created — source, contact validity, location, requirement signals, repeat-contact history. Point B (post-first-contact) and C (post-quotation) features are a deliberately separate, later extractor, so a model is never accidentally trained on information that wouldn't have existed yet at prediction time.
- **Every prediction carries its model version.** Non-negotiable per spec Phase 21 — without it, a score from before a retraining and a score from after are indistinguishable, and "was the model right" (Phase 23) becomes unanswerable.
- **Human override stays separate from the model.** A manager overriding a priority never changes what the model predicted — it's recorded as a business decision layered on top, both visible.

## When to revisit

Call `GET /crm/predictive-scoring/readiness`, or re-run the audit's queries. Don't resume this spec on a calendar schedule — on the data actually being there.
