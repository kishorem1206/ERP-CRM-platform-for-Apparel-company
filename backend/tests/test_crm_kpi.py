"""Tests for the CRM dashboard sales KPIs (app/services/crm_kpi.py).

The database tests build their scenarios inside one transaction and roll it
back at the end, so nothing is left behind in the database they run against.
Run from the backend container: python -m pytest tests/test_crm_kpi.py
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.company import Company
from app.models.crm import CrmLead, CrmLeadStageHistory, CrmPipeline, CrmPipelineStage
from app.services.crm_kpi import (
    CohortFilter,
    LeadFact,
    compare,
    load_cohort,
    previous_period,
    summarize,
)


def _fact(won=False, qualified=False, days_to_close=None, created=datetime(2026, 9, 1, tzinfo=timezone.utc)):
    closed = created + timedelta(days=days_to_close) if days_to_close is not None else None
    return LeadFact(created_at=created, closed_at=closed, is_won=won, is_qualified=qualified or won)


# ── Pure arithmetic ───────────────────────────────────────────────────────────

def test_spec_example_100_leads_30_qualified_10_won():
    facts = [_fact(won=True, days_to_close=5) for _ in range(10)]
    facts += [_fact(qualified=True) for _ in range(20)]
    facts += [_fact() for _ in range(70)]
    totals = summarize(facts)
    assert totals.new_leads == 100
    assert totals.qualified_leads == 30
    assert totals.lead_to_qualified_rate == 30.0
    assert totals.won_deals == 10
    assert totals.lead_to_won_conversion == 10.0


def test_zero_leads_gives_no_rates_and_no_time():
    totals = summarize([]).to_dict()
    assert totals["new_leads"] == 0
    assert totals["lead_to_qualified_rate"] is None
    assert totals["lead_to_won_conversion"] is None
    assert totals["avg_time_to_close_days"] is None


def test_leads_without_qualification_or_wins_have_zero_rates():
    totals = summarize([_fact(), _fact()])
    assert totals.lead_to_qualified_rate == 0.0
    assert totals.won_deals == 0
    assert totals.avg_time_to_close_days is None


def test_avg_time_to_close_uses_only_won_deals_with_a_close_time():
    facts = [
        _fact(won=True, days_to_close=35),
        _fact(won=True, days_to_close=26),
        _fact(won=True, days_to_close=1),
        _fact(qualified=True, days_to_close=10),
    ]
    totals = summarize(facts)
    assert totals.time_to_close_sample == 3
    assert round(totals.avg_time_to_close_days, 1) == 20.7


def test_won_without_closed_at_counts_as_won_but_not_in_time_average():
    fact = LeadFact(created_at=datetime(2026, 9, 1, tzinfo=timezone.utc), closed_at=None, is_won=True, is_qualified=True)
    totals = summarize([fact])
    assert totals.won_deals == 1
    assert totals.avg_time_to_close_days is None
    assert totals.time_to_close_sample == 0


def test_closed_before_created_is_excluded_from_time_average():
    created = datetime(2026, 9, 10, tzinfo=timezone.utc)
    bad = LeadFact(created_at=created, closed_at=created - timedelta(days=2), is_won=True, is_qualified=True)
    assert summarize([bad]).time_to_close_sample == 0


def test_comparison_relative_change_for_counts_and_points_for_rates():
    current = summarize([_fact(won=True, days_to_close=10)] + [_fact() for _ in range(3)])
    previous = summarize([_fact() for _ in range(2)])
    comparisons = compare(current, previous)
    assert comparisons["new_leads_change_pct"] == 100.0
    assert comparisons["won_deals_change_pct"] is None
    assert comparisons["won_conversion_change_pts"] == 25.0
    assert comparisons["qualification_rate_change_pts"] == 25.0


def test_previous_period_for_custom_range_has_same_length_and_no_overlap():
    start, end = previous_period(date(2026, 9, 10), date(2026, 9, 14))
    assert (end - start).days + 1 == 5
    assert end == date(2026, 9, 9)


def test_previous_period_for_full_calendar_units_is_the_previous_unit():
    assert previous_period(date(2026, 9, 1), date(2026, 9, 30)) == (date(2026, 8, 1), date(2026, 8, 31))
    assert previous_period(date(2026, 1, 1), date(2026, 1, 31)) == (date(2025, 12, 1), date(2025, 12, 31))
    assert previous_period(date(2026, 7, 1), date(2026, 9, 30)) == (date(2026, 4, 1), date(2026, 6, 30))
    assert previous_period(date(2026, 1, 1), date(2026, 3, 31)) == (date(2025, 10, 1), date(2025, 12, 31))
    assert previous_period(date(2026, 1, 1), date(2026, 12, 31)) == (date(2025, 1, 1), date(2025, 12, 31))


def test_comparison_with_empty_previous_period_is_null_not_division_error():
    comparisons = compare(summarize([_fact()]), summarize([]))
    assert comparisons["new_leads_change_pct"] is None
    assert comparisons["qualification_rate_change_pts"] is None
    assert comparisons["avg_time_to_close_change_days"] is None


# ── Cohort SQL against the database (rolled back) ─────────────────────────────

WINDOW = CohortFilter(date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))


def _at(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=timezone.utc)


async def _pipeline(db, company_id, name, with_qualification=True):
    now = datetime.now(timezone.utc)
    pipeline = CrmPipeline(id=uuid4(), company_id=company_id, name=name, is_default=False, rotten_days=30,
                           created_at=now, updated_at=now)
    db.add(pipeline)
    stages = {}
    for order, (label, is_won, is_lost) in enumerate(
        [("New", False, False), ("Qualified", False, False), ("Proposal", False, False),
         ("Negotiation", False, False), ("Won", True, False), ("Lost", False, True)], start=1
    ):
        stage = CrmPipelineStage(id=uuid4(), pipeline_id=pipeline.id, name=label, sort_order=order,
                                 is_won=is_won, is_lost=is_lost, created_at=now)
        db.add(stage)
        stages[label] = stage
    await db.flush()
    if with_qualification:
        pipeline.qualified_stage_id = stages["Qualified"].id
        await db.flush()
    return pipeline, stages


async def _lead(db, company_id, pipeline, stage, title, created, status="open", closed=None):
    lead = CrmLead(id=uuid4(), company_id=company_id, title=title, status=status, pipeline_id=pipeline.id,
                   stage_id=stage.id, created_at=created, updated_at=created, closed_at=closed,
                   lead_value=Decimal("0"))
    db.add(lead)
    await db.flush()
    return lead


async def _move(db, lead, from_stage, to_stage, at):
    db.add(CrmLeadStageHistory(lead_id=lead.id, from_stage_id=from_stage.id, to_stage_id=to_stage.id,
                               from_stage_name=from_stage.name, to_stage_name=to_stage.name, changed_at=at))
    await db.flush()


async def _run_cohort_scenarios():
    async with AsyncSessionLocal() as db:
        try:
            company_id = (await db.execute(select(Company.id).limit(1))).scalar_one()
            pipeline, s = await _pipeline(db, company_id, f"KPI test {uuid4().hex[:8]}")

            # Created in Sep, qualified later by a stage move.
            a = await _lead(db, company_id, pipeline, s["Qualified"], "A", _at(15), )
            await _move(db, a, s["New"], s["Qualified"], _at(20))
            # Created in Sep, won after the period.
            b = await _lead(db, company_id, pipeline, s["Won"], "B", _at(15), status="won", closed=_at(15) + timedelta(days=35))
            # Created in August, won in September: must not be in the September cohort.
            await _lead(db, company_id, pipeline, s["Won"], "C", datetime(2026, 8, 20, tzinfo=timezone.utc),
                        status="won", closed=_at(10))
            # Full journey, won.
            d = await _lead(db, company_id, pipeline, s["Won"], "D", _at(2), status="won", closed=_at(2) + timedelta(days=26))
            await _move(db, d, s["New"], s["Qualified"], _at(3))
            await _move(db, d, s["Qualified"], s["Proposal"], _at(10))
            await _move(db, d, s["Proposal"], s["Negotiation"], _at(15))
            await _move(db, d, s["Negotiation"], s["Won"], _at(28))
            # Qualified, then lost.
            e = await _lead(db, company_id, pipeline, s["Lost"], "E", _at(3), status="lost", closed=_at(25))
            await _move(db, e, s["New"], s["Qualified"], _at(5))
            await _move(db, e, s["Qualified"], s["Lost"], _at(25))
            # Qualified, then moved back to New.
            f = await _lead(db, company_id, pipeline, s["New"], "F", _at(4))
            await _move(db, f, s["New"], s["Qualified"], _at(6))
            await _move(db, f, s["Qualified"], s["New"], _at(7))
            # Never qualified.
            await _lead(db, company_id, pipeline, s["New"], "G", _at(5))
            # Skipped qualification entirely (no history): current stage is beyond it.
            await _lead(db, company_id, pipeline, s["Proposal"], "H", _at(6))
            # Lost with no history: no evidence it ever qualified.
            await _lead(db, company_id, pipeline, s["Lost"], "I", _at(7), status="lost", closed=_at(8))
            # Won straight from New (converted from the CRM).
            await _lead(db, company_id, pipeline, s["New"], "J", _at(8), status="won", closed=_at(9))

            facts, unconfigured = await load_cohort(db, company_id, CohortFilter(
                date_from=WINDOW.date_from, date_to=WINDOW.date_to, pipeline_id=pipeline.id))
            totals = summarize(facts)

            # Pipeline without a qualification stage: its leads are counted as unconfigured.
            bare_pipeline, bare_stages = await _pipeline(db, company_id, f"KPI bare {uuid4().hex[:8]}",
                                                         with_qualification=False)
            await _lead(db, company_id, bare_pipeline, bare_stages["Proposal"], "K", _at(10))
            bare_facts, bare_unconfigured = await load_cohort(db, company_id, CohortFilter(
                date_from=WINDOW.date_from, date_to=WINDOW.date_to, pipeline_id=bare_pipeline.id))

            return totals, unconfigured, bare_facts, bare_unconfigured
        finally:
            await db.rollback()


def test_cohort_scenarios_match_definitions():
    totals, unconfigured, bare_facts, bare_unconfigured = asyncio.run(_run_cohort_scenarios())

    # A, B, D, E, F, G, H, I, J are in the September cohort; C is not.
    assert totals.new_leads == 9
    # A (qualified later), B (won), D (full journey), E (qualified then lost),
    # F (qualified then moved back), H (skipped to Proposal), J (won from New).
    assert totals.qualified_leads == 7
    # B, D, J.
    assert totals.won_deals == 3
    assert round(totals.lead_to_won_conversion, 1) == 33.3
    assert round(totals.lead_to_qualified_rate, 1) == 77.8
    # 35 + 26 + 1 days over three won deals.
    assert totals.time_to_close_sample == 3
    assert round(totals.avg_time_to_close_days, 1) == 20.7
    assert unconfigured == 0

    assert len(bare_facts) == 1
    assert bare_unconfigured == 1
    assert summarize(bare_facts).qualified_leads == 0


# ── Open pipeline (current state and snapshot) ────────────────────────────────

from app.services.crm_kpi import LeadRecord, MoveRecord, StageRecord, compute_open_pipeline  # noqa: E402

_P = uuid4()
_NEW, _QUAL, _PROP, _WON, _LOST = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
_STAGES = {
    _NEW: StageRecord(_NEW, _P, "New", 1, False, False),
    _QUAL: StageRecord(_QUAL, _P, "Qualified", 2, False, False),
    _PROP: StageRecord(_PROP, _P, "Proposal", 3, False, False),
    _WON: StageRecord(_WON, _P, "Won", 4, True, False),
    _LOST: StageRecord(_LOST, _P, "Lost", 5, False, True),
}
_THRESHOLDS = {_P: 2}
_NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
_PREV_AT = datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc)


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _rec(name, created, stage, status="open", closed=None, value=0.0):
    lead_id = uuid4()
    return LeadRecord(lead_id, _P, stage, status, created, closed, value), name


def _mv(lead, frm, to, at):
    return MoveRecord(lead.id, frm, to, at)


def _fixture():
    specs = {}
    l1, _ = _rec("L1", _utc(2026, 8, 1), _PROP, value=100)
    l2, _ = _rec("L2", _utc(2026, 10, 1), _QUAL, value=200)
    l3, _ = _rec("L3", _utc(2026, 8, 15), _WON, status="won", closed=_utc(2026, 10, 3), value=300)
    l4, _ = _rec("L4", _utc(2026, 8, 10), _LOST, status="lost", closed=_utc(2026, 9, 20), value=50)
    l5, _ = _rec("L5", _utc(2026, 7, 1), _NEW, value=60)
    l6, _ = _rec("L6", _utc(2026, 8, 5), _PROP, value=300)
    l7, _ = _rec("L7", _utc(2026, 8, 20), _QUAL, closed=_utc(2026, 9, 25), value=400)
    l8, _ = _rec("L8", _utc(2026, 7, 10), _PROP, value=500)
    l10, _ = _rec("L10", _utc(2026, 8, 1), _WON, status="won", closed=None, value=0)
    l11, _ = _rec("L11", _utc(2026, 8, 2), _NEW, value=600)
    leads = [l1, l2, l3, l4, l5, l6, l7, l8, l10, l11]
    moves = {
        l2.id: [_mv(l2, _NEW, _QUAL, _utc(2026, 10, 2))],
        l3.id: [_mv(l3, _PROP, _WON, _utc(2026, 10, 3))],
        l6.id: [_mv(l6, _NEW, _PROP, _utc(2026, 9, 10))],
        l11.id: [_mv(l11, _NEW, _QUAL, _utc(2026, 9, 5)), _mv(l11, _QUAL, _NEW, _utc(2026, 10, 3))],
    }
    return leads, moves


def test_open_pipeline_current_state_and_ageing():
    leads, moves = _fixture()
    result = compute_open_pipeline(leads, moves, _STAGES, _THRESHOLDS, _NOW, _PREV_AT, True)
    assert result["open_count"] == 6
    assert result["open_value"] == 2100
    assert result["older_than_30_days_count"] == 5
    assert result["older_than_30_days_count"] <= result["open_count"]
    assert sum(r["count"] for r in result["by_stage"]) == result["open_count"]
    stage_counts = {r["stage_name"]: r["count"] for r in result["by_stage"]}
    assert stage_counts == {"New": 1, "Qualified": 2, "Proposal": 3}


def test_open_pipeline_movement_bridge_reconciles():
    leads, moves = _fixture()
    result = compute_open_pipeline(leads, moves, _STAGES, _THRESHOLDS, _NOW, _PREV_AT, True)
    assert result["previous"]["count"] == 5
    assert result["movement"] == {"added": 2, "won": 1, "lost": 0, "other": 0, "reconciles": True}
    assert result["change_pct"] == 20.0


def test_open_pipeline_notes_disclose_reopened_and_missing_close_dates():
    leads, moves = _fixture()
    result = compute_open_pipeline(leads, moves, _STAGES, _THRESHOLDS, _NOW, _PREV_AT, True)
    assert result["data_notes"]["reopened_count"] == 1
    assert result["data_notes"]["won_lost_without_close_date"] == 1
    assert result["data_notes"]["open_without_qualification_stage"] == 0


def test_open_pipeline_without_history_has_no_previous_value():
    leads, moves = _fixture()
    result = compute_open_pipeline(leads, moves, _STAGES, _THRESHOLDS, _NOW, _PREV_AT, False)
    assert result["previous"] is None
    assert result["movement"] is None
    assert result["change_pct"] is None
    assert result["open_count"] == 6


def test_open_pipeline_excludes_won_lost_and_unqualified():
    leads, moves = _fixture()
    result = compute_open_pipeline(leads, moves, _STAGES, _THRESHOLDS, _NOW, _PREV_AT, True)
    counted = {r["stage_name"] for r in result["by_stage"]}
    assert "Won" not in counted and "Lost" not in counted
    # L5 (open, still at New with no history) is open but not qualified.
    assert result["open_count"] == 6


def test_stage_at_past_instant_uses_first_later_move():
    from app.services.crm_kpi import _stage_at
    leads, moves = _fixture()
    l11 = next(l for l in leads if l.created_at == _utc(2026, 8, 2))
    assert _stage_at(l11, moves[l11.id], _utc(2026, 9, 1)) == _NEW
    assert _stage_at(l11, moves[l11.id], _utc(2026, 9, 6)) == _QUAL
    assert _stage_at(l11, moves[l11.id], None) == _NEW
