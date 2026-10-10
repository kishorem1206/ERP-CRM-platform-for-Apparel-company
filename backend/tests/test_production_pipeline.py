"""Tests for the Production module's core workflow logic
(app/services/production.py) — stage-type inference, size-wise quantity
propagation across stages (Phase 9/11), the stage-completion gate that
lets a lot advance status (Phase 11), and the size-wise double-booking
guard.

The database tests build their scenario inside one transaction and roll
it back at the end, so nothing is left behind in the database they run
against. Run from the backend container: python -m pytest tests/test_production_pipeline.py

Note: whichever async DB-backed test happens to run LAST in a given pytest
session (this file alone, or combined with other test files) reports a
cosmetic "Event loop is closed" RuntimeError during asyncpg connection-pool
teardown at interpreter shutdown — a pre-existing characteristic of this
repo's asyncio.run()-per-test pattern sharing one module-level engine
(reproducible the same way with tests/test_crm_kpi.py), not a real
assertion failure. Every test passes individually and the actual
assertions all run and pass before that teardown noise appears.
"""
import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domain.business_rules import BusinessRulesError
from app.models.master import Colour, Size
from app.models.user import User
from app.schemas.production import (
    LotSizeCreate, ProductionLotCreate, StageSizeUpdate,
    StageUpdate, StyleColourIn, StyleCreate, StyleProcessIn, StyleSizeIn, StyleSubProcessIn,
)
from app.services.production import ProductionService, QuantityValidationError


# ── Pure logic: stage-type inference (app/services/production.py) ───────────

def test_infer_stage_type_matches_keywords():
    svc = ProductionService.__new__(ProductionService)  # pure method, no db needed
    assert svc._infer_stage_type("Cutting") == "cutting"
    assert svc._infer_stage_type("Final Checking") == "qc"
    assert svc._infer_stage_type("Quality Inspection") == "qc"
    assert svc._infer_stage_type("Packing") == "packing"
    assert svc._infer_stage_type("Dispatch to Vendor") == "dispatch"
    assert svc._infer_stage_type("Ironing") == "finishing"


def test_infer_stage_type_falls_back_to_making():
    svc = ProductionService.__new__(ProductionService)
    assert svc._infer_stage_type("Stitching") == "making"
    assert svc._infer_stage_type("Something Unrecognised") == "making"


# ── DB-backed: full lot lifecycle through size-wise propagation ─────────────

async def _run_lot_lifecycle_scenario():
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            size_s = (await db.execute(select(Size.id).where(Size.company_id == company_id, Size.name == "S").limit(1))).scalar_one()
            size_m = (await db.execute(select(Size.id).where(Size.company_id == company_id, Size.name == "M").limit(1))).scalar_one()
            colour = (await db.execute(select(Colour.id).where(Colour.company_id == company_id).limit(1))).scalar_one()

            svc = ProductionService(db)
            style = await svc.create_style(
                StyleCreate(
                    name=f"Test Style {uuid4().hex[:8]}", final_output_unit="Pieces",
                    sizes=[StyleSizeIn(size_id=size_s, sort_order=1), StyleSizeIn(size_id=size_m, sort_order=2)],
                    colours=[StyleColourIn(colour_id=colour, sort_order=1)],
                    processes=[
                        StyleProcessIn(seq=1, process_name="Cutting"),
                        StyleProcessIn(seq=2, process_name="Checking"),
                    ],
                ),
                company_id, user_id,
            )
            lot = await svc.create_lot(
                ProductionLotCreate(
                    style_id=style.id, planned_qty=30, colour_id=colour,
                    sizes=[LotSizeCreate(size_id=size_s, planned_qty=10), LotSizeCreate(size_id=size_m, planned_qty=20)],
                ),
                company_id, user_id,
            )
            lot = await svc.get_lot(lot.id, company_id)
            cutting = next(s for s in lot.stages if s.stage_name == "Cutting")
            checking = next(s for s in lot.stages if s.stage_name == "Checking")

            # Checking's own size rows start at input_qty=0 (Phase 9's original
            # limitation) until Cutting's own size-wise acceptance propagates in.
            checking_before = {sz.size_id: sz.input_qty for sz in checking.sizes}

            # Accept 9 of 10 (S) and 18 of 20 (M) at Cutting.
            await svc.update_stage_size(cutting.id, size_s, StageSizeUpdate(accepted_qty=9, rejected_qty=1, rework_qty=0), company_id)
            await svc.update_stage_size(cutting.id, size_m, StageSizeUpdate(accepted_qty=18, rejected_qty=2, rework_qty=0), company_id)
            await db.flush()

            lot = await svc.get_lot(lot.id, company_id)
            checking = next(s for s in lot.stages if s.stage_name == "Checking")
            checking_after = {sz.size_id: sz.input_qty for sz in checking.sizes}

            # Over-accepting at Checking (more than what Cutting actually passed
            # down) must still be rejected by the same per-size validation.
            overbook_error = None
            try:
                await svc.update_stage_size(checking.id, size_s, StageSizeUpdate(accepted_qty=10, rejected_qty=0, rework_qty=0), company_id)
            except QuantityValidationError as e:
                overbook_error = str(e)

            # Accept the real 9 at Checking, then try to advance the lot before
            # any stage is marked "completed" — this must be blocked.
            await svc.update_stage_size(checking.id, size_s, StageSizeUpdate(accepted_qty=9, rejected_qty=0, rework_qty=0), company_id)
            await db.flush()

            premature_advance_error = None
            try:
                await svc.advance_lot_status(lot.id, company_id, "checking")
            except BusinessRulesError as e:
                premature_advance_error = e.message

            # Mark every stage completed, then the same advance must succeed.
            lot = await svc.get_lot(lot.id, company_id)
            for s in sorted(lot.stages, key=lambda st: st.created_at):
                await svc.update_stage(s.id, StageUpdate(status="completed"), company_id)
            await db.flush()
            advanced = await svc.advance_lot_status(lot.id, company_id, "checking")

            return {
                "checking_before": checking_before, "checking_after": checking_after,
                "size_s": size_s, "size_m": size_m,
                "overbook_error": overbook_error, "premature_advance_error": premature_advance_error,
                "advanced_status": advanced.status if advanced else None,
            }
        finally:
            await db.rollback()


def test_size_wise_propagation_and_lot_lifecycle():
    r = asyncio.run(_run_lot_lifecycle_scenario())

    # Before Cutting's acceptance, Checking had no size-wise input at all
    # (the original Phase 9 limitation this session's fix closes).
    assert r["checking_before"][r["size_s"]] == 0
    assert r["checking_before"][r["size_m"]] == 0

    # After Cutting accepts 9/18, Checking's own per-size input_qty mirrors it.
    assert r["checking_after"][r["size_s"]] == 9
    assert r["checking_after"][r["size_m"]] == 18

    # Accepting more at Checking than Cutting actually passed down is rejected.
    assert r["overbook_error"] is not None
    assert "cannot exceed" in r["overbook_error"]

    # A lot cannot advance status while any stage of the current bucket is
    # still not marked "completed" — the gap this session's Phase 11 work closed
    # (nothing could ever set that status before this fix existed).
    assert r["premature_advance_error"] is not None
    assert "still in progress" in r["premature_advance_error"]

    # Once every stage is marked completed, the advance succeeds.
    assert r["advanced_status"] == "checking"


# ── Regression: create_lot's own response must not crash ────────────────────

async def _run_create_lot_response_scenario():
    """create_lot's own final re-fetch (used directly by the real
    POST /production/lots response, via _lot_out/_stage_out) must eager-load
    everything _stage_out reads — stage.sizes and stage.style_process.
    sub_processes — or building the response crashes with MissingGreenlet
    for every single lot created from a style with sizes and sub-processes
    (which is most real styles). Found by calling _lot_out on create_lot's
    own return value directly, exactly as the endpoint does, instead of the
    follow-up get_lot() every other script in this project had been using
    instead (which has always eager-loaded this correctly and so never
    exposed the gap in create_lot's own query)."""
    from app.api.v1.endpoints.production import _lot_out

    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            size_s = (await db.execute(select(Size.id).where(Size.company_id == company_id, Size.name == "S").limit(1))).scalar_one()
            colour = (await db.execute(select(Colour.id).where(Colour.company_id == company_id).limit(1))).scalar_one()

            svc = ProductionService(db)
            style = await svc.create_style(
                StyleCreate(
                    name=f"Test Style {uuid4().hex[:8]}", final_output_unit="Pieces",
                    sizes=[StyleSizeIn(size_id=size_s, sort_order=1)],
                    colours=[StyleColourIn(colour_id=colour, sort_order=1)],
                    processes=[StyleProcessIn(seq=1, process_name="Cutting", planned_rate=10,
                                               sub_processes=[StyleSubProcessIn(seq=1, name="Spreading", planned_rate=5)])],
                ),
                company_id, user_id,
            )
            lot = await svc.create_lot(
                ProductionLotCreate(style_id=style.id, planned_qty=10, colour_id=colour,
                                     sizes=[LotSizeCreate(size_id=size_s, planned_qty=10)]),
                company_id, user_id,
            )
            out = await _lot_out(lot, svc)
            cutting = next(s for s in out.stages if s.stage_name == "Cutting")
            return {"input_qty": cutting.sizes[0].input_qty, "operation_name": cutting.operations[0].name}
        finally:
            await db.rollback()


def test_create_lot_response_does_not_crash_on_sizes_or_operations():
    r = asyncio.run(_run_create_lot_response_scenario())
    assert r["input_qty"] == 10
    assert r["operation_name"] == "Spreading"


async def _run_list_lots_response_scenario():
    """GET /production/lots serializes every row through _lot_out; list_lots
    used to keep its own (shorter) eager-load list and crashed the whole
    lots page once _stage_out began reading stage.sizes/sub_processes."""
    from app.api.v1.endpoints.production import _lot_out

    async with AsyncSessionLocal() as db:
        try:
            company_id = (await db.execute(select(User.company_id).limit(1))).scalar_one()
            svc = ProductionService(db)
            lots, _ = await svc.list_lots(company_id, page_size=20)
            return [(await _lot_out(lot, svc)).lot_number for lot in lots]
        finally:
            await db.rollback()


def test_list_lots_response_does_not_crash():
    numbers = asyncio.run(_run_list_lots_response_scenario())
    assert isinstance(numbers, list)
