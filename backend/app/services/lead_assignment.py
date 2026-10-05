"""Smart lead assignment (Phase 2, spec Steps 1-3): rule-based first, then
round-robin fallback. Manual assignment already existed before this file -
the existing `assigned_to` field and `/leads/{id}/assign` endpoint are
untouched; this only adds what picks an assignee *automatically* when
nobody picked one by hand.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import (
    CrmLead, CrmLeadAssignmentPool, CrmLeadAssignmentRule, CrmPerson, CrmRoundRobinState,
)
from app.services.lead_intelligence import get_location_tier


async def _find_matching_rule(db: AsyncSession, lead: CrmLead, city: Optional[str]) -> Optional[UUID]:
    rules = (await db.execute(
        select(CrmLeadAssignmentRule)
        .where(CrmLeadAssignmentRule.company_id == lead.company_id, CrmLeadAssignmentRule.is_active.is_(True))
        .order_by(CrmLeadAssignmentRule.sort_order)
    )).scalars().all()
    if not rules:
        return None

    tier = await get_location_tier(db, lead.company_id, city) if any(r.location_tier for r in rules) else None

    for rule in rules:
        if rule.source_id is not None and rule.source_id != lead.source_id:
            continue
        if rule.min_score is not None and (lead.score is None or lead.score < rule.min_score):
            continue
        if rule.location_tier is not None and rule.location_tier != tier:
            continue
        return rule.assign_to
    return None


async def _next_round_robin_user(db: AsyncSession, company_id: UUID) -> Optional[UUID]:
    pool = (await db.execute(
        select(CrmLeadAssignmentPool)
        .where(CrmLeadAssignmentPool.company_id == company_id, CrmLeadAssignmentPool.is_active.is_(True))
        .order_by(CrmLeadAssignmentPool.sort_order)
    )).scalars().all()
    if not pool:
        return None

    state = (await db.execute(
        select(CrmRoundRobinState).where(CrmRoundRobinState.company_id == company_id)
    )).scalar_one_or_none()

    ids = [m.user_id for m in pool]
    if state and state.last_assigned_user_id in ids:
        next_user = ids[(ids.index(state.last_assigned_user_id) + 1) % len(ids)]
    else:
        next_user = ids[0]

    now = datetime.now(timezone.utc)
    if state:
        state.last_assigned_user_id = next_user
        state.updated_at = now
    else:
        db.add(CrmRoundRobinState(company_id=company_id, last_assigned_user_id=next_user, updated_at=now))
    return next_user


async def auto_assign_lead(db: AsyncSession, lead: CrmLead) -> Optional[UUID]:
    """Picks an assignee for a lead that doesn't have one yet: the first
    matching rule, falling back to round-robin over the active pool.
    Returns None (stays unassigned) if neither has anything configured -
    this never invents an assignee out of nowhere."""
    city = None
    if lead.person_id:
        person = (await db.execute(select(CrmPerson).where(CrmPerson.id == lead.person_id))).scalar_one_or_none()
        city = person.city if person else None

    rule_match = await _find_matching_rule(db, lead, city)
    if rule_match:
        return rule_match
    return await _next_round_robin_user(db, lead.company_id)


def response_target_for_priority(priority: Optional[str], company) -> Optional[datetime]:
    """The deadline implied by a lead's priority, from the company's
    configurable targets (spec Step 3)."""
    now = datetime.now(timezone.utc)
    if priority == "high":
        return now + timedelta(minutes=company.response_target_high_minutes)
    if priority == "medium":
        return now + timedelta(hours=company.response_target_medium_hours)
    if priority == "low":
        return now + timedelta(hours=company.response_target_low_hours)
    return None
