"""Core sales KPIs for the CRM dashboard.

One definition of the lead cohort and of each outcome. The KPI endpoint and
the drill-down lead list both call into this module, so a number on a card
and the leads behind it cannot disagree. Definitions are in
docs/CRM_DASHBOARD_KPI_DEFINITIONS.md.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import ColumnElement

from app.models.crm import CrmLead, CrmLeadStageHistory, CrmPipeline, CrmPipelineStage


def _day_start(day: date, utc_offset_minutes: int) -> datetime:
    """Start of a browser-local calendar day, as a UTC instant."""
    return datetime.combine(day, time.min, tzinfo=timezone.utc) - timedelta(minutes=utc_offset_minutes)


def created_in_period(
    company_id: UUID, date_from: date, date_to: date, utc_offset_minutes: int = 0
) -> list[ColumnElement[bool]]:
    return [
        CrmLead.company_id == company_id,
        CrmLead.created_at >= _day_start(date_from, utc_offset_minutes),
        CrmLead.created_at < _day_start(date_to + timedelta(days=1), utc_offset_minutes),
    ]


def _qualification_threshold():
    """sort_order of the qualification stage configured on the lead's own pipeline."""
    qualifying = aliased(CrmPipelineStage)
    return (
        select(qualifying.sort_order)
        .join(CrmPipeline, CrmPipeline.qualified_stage_id == qualifying.id)
        .where(CrmPipeline.id == CrmLead.pipeline_id)
        .correlate(CrmLead)
        .scalar_subquery()
    )


def qualified_clause() -> ColumnElement[bool]:
    """A lead is qualified if it has ever reached the pipeline's qualification stage or any later stage, or was won."""
    threshold = _qualification_threshold()

    current = aliased(CrmPipelineStage)
    reached_now = (
        select(current.id)
        .where(
            current.id == CrmLead.stage_id,
            current.pipeline_id == CrmLead.pipeline_id,
            current.sort_order >= threshold,
            current.is_lost.is_(False),
        )
        .exists()
    )

    visited = aliased(CrmPipelineStage)
    reached_before = (
        select(CrmLeadStageHistory.id)
        .join(visited, visited.id == CrmLeadStageHistory.to_stage_id)
        .where(
            CrmLeadStageHistory.lead_id == CrmLead.id,
            visited.pipeline_id == CrmLead.pipeline_id,
            visited.sort_order >= threshold,
            visited.is_lost.is_(False),
        )
        .exists()
    )

    return or_(CrmLead.status == "won", reached_now, reached_before)


def _pipeline_has_qualification_stage() -> ColumnElement[bool]:
    return (
        select(CrmPipeline.id)
        .where(CrmPipeline.id == CrmLead.pipeline_id, CrmPipeline.qualified_stage_id.is_not(None))
        .exists()
    )


@dataclass(frozen=True)
class CohortFilter:
    date_from: date
    date_to: date
    utc_offset_minutes: int = 0
    pipeline_id: UUID | None = None
    assigned_to: UUID | None = None
    source_id: UUID | None = None


@dataclass(frozen=True)
class LeadFact:
    created_at: datetime
    closed_at: datetime | None
    is_won: bool
    is_qualified: bool


async def load_cohort(db: AsyncSession, company_id: UUID, f: CohortFilter) -> tuple[list[LeadFact], int]:
    """Leads created in the period, with their outcomes; also counts leads whose pipeline has no qualification stage set."""
    conditions = created_in_period(company_id, f.date_from, f.date_to, f.utc_offset_minutes)
    if f.pipeline_id:
        conditions.append(CrmLead.pipeline_id == f.pipeline_id)
    if f.assigned_to:
        conditions.append(CrmLead.assigned_to == f.assigned_to)
    if f.source_id:
        conditions.append(CrmLead.source_id == f.source_id)

    result = await db.execute(
        select(
            CrmLead.created_at,
            CrmLead.closed_at,
            (CrmLead.status == "won").label("is_won"),
            qualified_clause().label("is_qualified"),
            _pipeline_has_qualification_stage().label("configured"),
        ).where(*conditions)
    )
    rows = result.all()
    facts = [
        LeadFact(
            created_at=row.created_at,
            closed_at=row.closed_at,
            is_won=bool(row.is_won),
            is_qualified=bool(row.is_qualified),
        )
        for row in rows
    ]
    unconfigured = sum(1 for row in rows if not row.configured)
    return facts, unconfigured


@dataclass(frozen=True)
class KpiTotals:
    new_leads: int
    qualified_leads: int
    lead_to_qualified_rate: float | None
    won_deals: int
    lead_to_won_conversion: float | None
    avg_time_to_close_days: float | None
    time_to_close_sample: int

    def to_dict(self) -> dict:
        data = asdict(self)
        data["lead_to_qualified_rate"] = _round(self.lead_to_qualified_rate, 1)
        data["lead_to_won_conversion"] = _round(self.lead_to_won_conversion, 1)
        data["avg_time_to_close_days"] = _round(self.avg_time_to_close_days, 1)
        return data


def _round(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _percent(part: int, whole: int) -> float | None:
    return None if whole == 0 else part / whole * 100


def summarize(facts: list[LeadFact]) -> KpiTotals:
    won = [f for f in facts if f.is_won]
    durations_days = [
        (f.closed_at - f.created_at).total_seconds() / 86400
        for f in won
        if f.closed_at is not None and f.closed_at >= f.created_at
    ]
    qualified = sum(1 for f in facts if f.is_qualified)
    return KpiTotals(
        new_leads=len(facts),
        qualified_leads=qualified,
        lead_to_qualified_rate=_percent(qualified, len(facts)),
        won_deals=len(won),
        lead_to_won_conversion=_percent(len(won), len(facts)),
        avg_time_to_close_days=sum(durations_days) / len(durations_days) if durations_days else None,
        time_to_close_sample=len(durations_days),
    )


def _pct_change(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def _difference(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def compare(current: KpiTotals, previous: KpiTotals) -> dict:
    return {
        "new_leads_change_pct": _round(_pct_change(current.new_leads, previous.new_leads), 1),
        "qualified_leads_change_pct": _round(_pct_change(current.qualified_leads, previous.qualified_leads), 1),
        "qualification_rate_change_pts": _round(
            _difference(current.lead_to_qualified_rate, previous.lead_to_qualified_rate), 1
        ),
        "won_deals_change_pct": _round(_pct_change(current.won_deals, previous.won_deals), 1),
        "won_conversion_change_pts": _round(
            _difference(current.lead_to_won_conversion, previous.lead_to_won_conversion), 1
        ),
        "avg_time_to_close_change_days": _round(
            _difference(current.avg_time_to_close_days, previous.avg_time_to_close_days), 1
        ),
    }


def _month_end(year: int, month: int) -> date:
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def previous_period(date_from: date, date_to: date) -> tuple[date, date]:
    """The period to compare against: the previous calendar month, quarter or year
    when the selection is exactly one of those; otherwise the immediately preceding
    period of the same length."""
    if date_from.day == 1:
        if date_from.month == 1 and date_to == date(date_from.year, 12, 31):
            return date(date_from.year - 1, 1, 1), date(date_from.year - 1, 12, 31)
        if (date_from.month - 1) % 3 == 0 and date_to == _month_end(*_shift_month(date_from.year, date_from.month, 2)):
            y, m = _shift_month(date_from.year, date_from.month, -3)
            return date(y, m, 1), _month_end(*_shift_month(y, m, 2))
        if date_to == _month_end(date_from.year, date_from.month):
            y, m = _shift_month(date_from.year, date_from.month, -1)
            return date(y, m, 1), _month_end(y, m)
    span = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span - 1)
    return prev_from, prev_to


OPEN_AGE_DAYS = 30


@dataclass(frozen=True)
class LeadRecord:
    id: UUID
    pipeline_id: UUID | None
    stage_id: UUID | None
    status: str
    created_at: datetime
    closed_at: datetime | None
    lead_value: float


@dataclass(frozen=True)
class StageRecord:
    id: UUID
    pipeline_id: UUID
    name: str
    sort_order: int
    is_won: bool
    is_lost: bool


@dataclass(frozen=True)
class MoveRecord:
    lead_id: UUID
    from_stage_id: UUID | None
    to_stage_id: UUID | None
    changed_at: datetime


def _is_terminal(stages: dict[UUID, StageRecord], stage_id: UUID | None) -> bool:
    stage = stages.get(stage_id) if stage_id else None
    return stage is not None and (stage.is_won or stage.is_lost)


def _stage_at(lead: LeadRecord, moves: list[MoveRecord], at: datetime | None) -> UUID | None:
    """Stage at a past instant, rebuilt from history; the current stage when at is None.

    Exact for instants on or after the first recorded move: the first move after
    the instant tells us the stage just before it.
    """
    if at is None:
        return lead.stage_id
    later = [m for m in moves if m.changed_at > at]
    if later:
        return later[0].from_stage_id
    earlier = [m for m in moves if m.changed_at <= at]
    if earlier:
        return earlier[-1].to_stage_id
    return lead.stage_id


def _is_open_at(lead: LeadRecord, at: datetime | None) -> bool:
    if at is None:
        return lead.status == "open"
    if lead.created_at > at:
        return False
    if lead.closed_at is not None:
        # Approximation: a reopened lead keeps its first close time.
        return lead.closed_at > at
    # Closed status with no close time: when it closed is unknown, so it cannot be placed in a past snapshot.
    return lead.status == "open"


def _is_qualified_at(
    lead: LeadRecord,
    stages: dict[UUID, StageRecord],
    thresholds: dict[UUID, int],
    moves: list[MoveRecord],
    at: datetime | None,
) -> bool:
    if lead.status == "won" and (at is None or (lead.closed_at is not None and lead.closed_at <= at)):
        return True
    threshold = thresholds.get(lead.pipeline_id)
    if threshold is None:
        return False

    def reached(stage_id: UUID | None) -> bool:
        stage = stages.get(stage_id) if stage_id else None
        return (
            stage is not None
            and stage.pipeline_id == lead.pipeline_id
            and stage.sort_order >= threshold
            and not stage.is_lost
        )

    if reached(_stage_at(lead, moves, at)):
        return True
    visible = moves if at is None else [m for m in moves if m.changed_at <= at]
    return any(reached(m.to_stage_id) for m in visible)


def compute_open_pipeline(
    leads: list[LeadRecord],
    moves_by_lead: dict[UUID, list[MoveRecord]],
    stages: dict[UUID, StageRecord],
    thresholds: dict[UUID, int],
    now: datetime,
    previous_at: datetime,
    previous_available: bool,
) -> dict:
    """Current open qualified pipeline, its ageing and stage split, and the movement since the previous reference date.

    The same function produces the current state (at = None) and the previous snapshot (at = previous_at),
    so the two cannot follow different rules. Movement is a bridge: previous + added - won - lost - other = current.
    """
    for moves in moves_by_lead.values():
        moves.sort(key=lambda m: m.changed_at)
    no_moves: list[MoveRecord] = []

    def open_qualified(lead: LeadRecord, at: datetime | None) -> bool:
        moves = moves_by_lead.get(lead.id, no_moves)
        return (
            _is_open_at(lead, at)
            and not _is_terminal(stages, _stage_at(lead, moves, at))
            and _is_qualified_at(lead, stages, thresholds, moves, at)
        )

    current = {lead.id: lead for lead in leads if open_qualified(lead, None)}
    open_value = sum(lead.lead_value for lead in current.values())
    aged_cutoff = now - timedelta(days=OPEN_AGE_DAYS)
    aged = sum(1 for lead in current.values() if lead.created_at < aged_cutoff)

    by_stage: dict[UUID, dict] = {}
    for lead in current.values():
        stage = stages[lead.stage_id]
        row = by_stage.setdefault(stage.id, {
            "stage_id": str(stage.id), "stage_name": stage.name, "sort_order": stage.sort_order,
            "pipeline_id": str(stage.pipeline_id), "count": 0, "value": 0.0,
        })
        row["count"] += 1
        row["value"] += lead.lead_value
    stage_rows = sorted(by_stage.values(), key=lambda r: (r["pipeline_id"], r["sort_order"]))

    open_without_stage = sum(
        1 for lead in leads
        if _is_open_at(lead, None) and lead.pipeline_id not in thresholds
    )
    open_at_terminal_stage = sum(
        1 for lead in leads
        if lead.status == "open" and _is_terminal(stages, lead.stage_id)
    )
    notes = {
        "reopened_count": sum(1 for lead in leads if lead.status == "open" and lead.closed_at is not None),
        "won_lost_without_close_date": sum(
            1 for lead in leads if lead.status in ("won", "lost") and lead.closed_at is None
        ),
        "open_without_qualification_stage": open_without_stage,
        "open_status_at_terminal_stage": open_at_terminal_stage,
    }

    previous = None
    movement = None
    change_pct = None
    if previous_available:
        prev = {lead.id: lead for lead in leads if open_qualified(lead, previous_at)}
        added = [lid for lid in current if lid not in prev]
        won = [lid for lid, l in prev.items() if lid not in current and l.status == "won" and l.closed_at and previous_at < l.closed_at <= now]
        lost = [lid for lid, l in prev.items() if lid not in current and l.status == "lost" and l.closed_at and previous_at < l.closed_at <= now]
        other = [lid for lid in prev if lid not in current and lid not in won and lid not in lost]
        movement = {"added": len(added), "won": len(won), "lost": len(lost), "other": len(other)}
        movement["reconciles"] = len(prev) + len(added) - len(won) - len(lost) - len(other) == len(current)
        previous = {"count": len(prev)}
        change_pct = _pct_change(len(current), len(prev)) if prev else None

    return {
        "open_count": len(current),
        "open_value": round(open_value, 2),
        "older_than_30_days_count": aged,
        "by_stage": stage_rows,
        "previous": previous,
        "change_pct": _round(change_pct, 1),
        "movement": movement,
        "data_notes": notes,
    }


@dataclass(frozen=True)
class OpenPipelineFilter:
    pipeline_id: UUID | None = None
    assigned_to: UUID | None = None
    source_id: UUID | None = None


async def load_open_pipeline(
    db: AsyncSession, company_id: UUID, f: OpenPipelineFilter, now: datetime, utc_offset_minutes: int = 0
) -> dict:
    stage_rows = (await db.execute(
        select(CrmPipelineStage.id, CrmPipelineStage.pipeline_id, CrmPipelineStage.name,
               CrmPipelineStage.sort_order, CrmPipelineStage.is_won, CrmPipelineStage.is_lost)
        .join(CrmPipeline, CrmPipeline.id == CrmPipelineStage.pipeline_id)
        .where(CrmPipeline.company_id == company_id)
    )).all()
    stages = {r.id: StageRecord(r.id, r.pipeline_id, r.name, r.sort_order, r.is_won, r.is_lost) for r in stage_rows}

    threshold_rows = (await db.execute(
        select(CrmPipeline.id, CrmPipelineStage.sort_order)
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmPipeline.qualified_stage_id)
        .where(CrmPipeline.company_id == company_id)
    )).all()
    thresholds = {r.id: r.sort_order for r in threshold_rows}

    conditions = [CrmLead.company_id == company_id]
    if f.pipeline_id:
        conditions.append(CrmLead.pipeline_id == f.pipeline_id)
    if f.assigned_to:
        conditions.append(CrmLead.assigned_to == f.assigned_to)
    if f.source_id:
        conditions.append(CrmLead.source_id == f.source_id)
    lead_rows = (await db.execute(select(CrmLead).where(*conditions))).scalars().all()
    leads = [
        LeadRecord(l.id, l.pipeline_id, l.stage_id, l.status, l.created_at, l.closed_at, float(l.lead_value or 0))
        for l in lead_rows
    ]

    move_rows = (await db.execute(
        select(CrmLeadStageHistory.lead_id, CrmLeadStageHistory.from_stage_id,
               CrmLeadStageHistory.to_stage_id, CrmLeadStageHistory.changed_at)
        .join(CrmLead, CrmLead.id == CrmLeadStageHistory.lead_id)
        .where(CrmLead.company_id == company_id)
    )).all()
    moves_by_lead: dict[UUID, list[MoveRecord]] = {}
    for r in move_rows:
        moves_by_lead.setdefault(r.lead_id, []).append(
            MoveRecord(r.lead_id, r.from_stage_id, r.to_stage_id, r.changed_at)
        )

    coverage_start = (await db.execute(
        select(func.min(CrmLeadStageHistory.changed_at))
        .join(CrmLead, CrmLead.id == CrmLeadStageHistory.lead_id)
        .where(CrmLead.company_id == company_id)
    )).scalar()

    local_today = (now + timedelta(minutes=utc_offset_minutes)).date()
    reference_day = local_today.replace(day=1) - timedelta(days=1)
    previous_at = _day_start(reference_day + timedelta(days=1), utc_offset_minutes) - timedelta(microseconds=1)
    previous_available = coverage_start is not None and previous_at >= coverage_start

    result = compute_open_pipeline(
        leads, moves_by_lead, stages, thresholds, now, previous_at, previous_available
    )
    result["previous"] = {
        "reference_date": reference_day.isoformat(),
        "available": previous_available,
        "count": result["previous"]["count"] if result["previous"] else None,
        "stage_history_since": coverage_start.isoformat() if coverage_start else None,
    }
    return result


QUALITY_TIERS = ("high", "medium", "low", "unscored")


async def lead_quality_breakdown(db: AsyncSession, company_id: UUID, f: CohortFilter) -> list[dict]:
    """Cohort leads grouped by quality tier (priority from scoring), with average score and outcomes."""
    conditions = created_in_period(company_id, f.date_from, f.date_to, f.utc_offset_minutes)
    if f.pipeline_id:
        conditions.append(CrmLead.pipeline_id == f.pipeline_id)
    if f.assigned_to:
        conditions.append(CrmLead.assigned_to == f.assigned_to)
    if f.source_id:
        conditions.append(CrmLead.source_id == f.source_id)

    tier = func.coalesce(CrmLead.priority, "unscored")
    rows = (await db.execute(
        select(
            tier.label("tier"),
            func.count(CrmLead.id).label("leads"),
            func.avg(CrmLead.score).label("avg_score"),
            func.count(CrmLead.id).filter(CrmLead.status == "won").label("won"),
            func.count(CrmLead.id).filter(CrmLead.status == "open").label("open"),
        ).where(*conditions).group_by(tier)
    )).all()
    by_tier = {r.tier: r for r in rows}
    total = sum(r.leads for r in rows)
    result = []
    for name in QUALITY_TIERS:
        r = by_tier.get(name)
        leads = r.leads if r else 0
        result.append({
            "tier": name,
            "leads": leads,
            "share_pct": round(leads / total * 100, 1) if total else None,
            "average_score": round(float(r.avg_score), 1) if r and r.avg_score is not None else None,
            "won": r.won if r else 0,
            "open": r.open if r else 0,
        })
    return result
