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
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domain.business_rules import BusinessRulesError
from app.models.master import Colour, Product, Size, Unit, Warehouse
from app.models.inventory import InventoryLot
from app.models.user import User
from app.schemas.materials import FabricCreate
from app.schemas.production import (
    LotMaterialCreate, LotMaterialUpdate, LotSizeCreate, ProductionLotCreate, StageEntryCreate, StageSizeUpdate,
    StageUpdate, StyleColourIn, StyleCreate, StyleFabricIn, StylePackingMaterialIn, StyleProcessIn, StyleSizeIn,
    StyleSubProcessIn, StyleTrimIn, StyleYarnIn,
)
from app.services.materials import MaterialsService
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


async def _run_gram_fabric_scenario():
    """A Style's consumption can be in grams per piece, but a lot must carry it
    as kg: yarn requirements are a share of that number and are themselves kg."""
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            colour = (await db.execute(select(Colour.id).where(Colour.company_id == company_id).limit(1))).scalar_one()
            svc = ProductionService(db)
            style = await svc.create_style(
                StyleCreate(
                    name=f"Test Style {uuid4().hex[:8]}", final_output_unit="Pieces",
                    fabrics=[
                        StyleFabricIn(fabric_name="Gram Fabric", consumption=200, unit="g", excess_pct=10),
                        StyleFabricIn(fabric_name="Kg Fabric", consumption="0.5", unit="kg"),
                        StyleFabricIn(fabric_name="Metre Fabric", consumption="1.5", unit="m"),
                    ],
                    yarns=[StyleYarnIn(yarn_name="Gram Fabric Yarn", fabric_index=0, consumption_pct=100, unit="kg")],
                ),
                company_id, user_id,
            )
            lot = await svc.create_lot(ProductionLotCreate(style_id=style.id, planned_qty=100, colour_id=colour), company_id, user_id)
            lot = await svc.get_lot(lot.id, company_id)
            return (
                {f.fabric_name: (float(f.planned_qty), f.unit) for f in lot.lot_fabrics},
                {y.yarn_name: (float(y.planned_qty), y.unit) for y in lot.lot_yarns},
            )
        finally:
            await db.rollback()


def test_gram_fabric_consumption_becomes_kg_on_the_lot():
    fabrics, yarns = asyncio.run(_run_gram_fabric_scenario())
    # 200 g x 100 pcs x 1.10 excess = 22 kg, not 22,000.
    assert fabrics["Gram Fabric"] == (22.0, "kg")
    assert yarns["Gram Fabric Yarn"] == (22.0, "kg")
    # Other units pass through unchanged.
    assert fabrics["Kg Fabric"] == (50.0, "kg")
    assert fabrics["Metre Fabric"] == (150.0, "m")


async def _run_lot_link_scenario():
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            fabric_a, fabric_b = (await db.execute(
                select(Product.id).where(Product.company_id == company_id, Product.product_type == "fabric").limit(2)
            )).scalars().all()
            yarn = (await db.execute(
                select(Product.id).where(Product.company_id == company_id, Product.product_type == "yarn").limit(1)
            )).scalar_one()
            warehouse = (await db.execute(select(Warehouse.id).where(Warehouse.company_id == company_id).limit(1))).scalar_one()
            kg = (await db.execute(select(Unit.id).where(Unit.abbreviation == "kg", Unit.company_id == company_id).limit(1))).scalar_one()
            svc = MaterialsService(db)

            async def rejected(lot_id, product_id):
                try:
                    await svc.link_lot_product(lot_id, product_id, company_id)
                except BusinessRulesError as e:
                    return e.code
                return None

            empty = await svc.create_fabric(FabricCreate(lot_number=f"T-{uuid4().hex[:8]}"), company_id, user_id)
            wrong_type = await rejected(empty.id, yarn)
            await svc.link_lot_product(empty.id, fabric_a, company_id)
            relinked = (await svc.link_lot_product(empty.id, fabric_b, company_id)).product_id
            unlinked = (await svc.link_lot_product(empty.id, None, company_id)).product_id

            # Stocked under fabric_a, but the lot itself left unlinked: the
            # state an existing lot can be in.
            stocked = await svc.create_fabric(
                FabricCreate(
                    lot_number=f"T-{uuid4().hex[:8]}", product_id=fabric_a, warehouse_id=warehouse,
                    unit_id=kg, quantity=10, unit_cost=100,
                ),
                company_id, user_id,
            )
            stocked.product_id = None
            await db.flush()
            other_product = await rejected(stocked.id, fabric_b)
            lot_after_reject = (await db.execute(select(InventoryLot.product_id).where(InventoryLot.id == stocked.id))).scalar_one()
            await svc.link_lot_product(stocked.id, fabric_a, company_id)
            unlink_stocked = await rejected(stocked.id, None)
            layers = await svc.inv._get_fifo_layers(company_id, fabric_a, warehouse, None)
            return {
                "wrong_type": wrong_type, "relinked": relinked == fabric_b, "unlinked": unlinked,
                "other_product": other_product, "lot_after_reject": lot_after_reject,
                "unlink_stocked": unlink_stocked, "in_fifo": stocked.id in {l[0] for l in layers},
            }
        finally:
            await db.rollback()


def test_lot_product_link_keeps_stock_under_its_own_product():
    r = asyncio.run(_run_lot_link_scenario())
    # No stock records: free to link, change and remove.
    assert r["wrong_type"] == "INVALID_LOT_PRODUCT"
    assert r["relinked"] is True
    assert r["unlinked"] is None
    # Stock records: only the product they are under.
    assert r["other_product"] == "LOT_HAS_STOCK"
    assert r["lot_after_reject"] is None
    assert r["unlink_stocked"] == "LOT_HAS_STOCK"
    assert r["in_fifo"] is True


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


async def _run_cutting_entry_scenario():
    """Cutting is logged as fabric kg in and pieces out: its pieces "in" are the
    pieces it cut, and what it passes on becomes the next stage's plan. A lot
    with no colour must be creatable too."""
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            svc = ProductionService(db)
            # No style, so the generic stages apply (Cutting then Making) and
            # there is no fabric gate to satisfy first.
            lot = await svc.create_lot(ProductionLotCreate(planned_qty=100), company_id, user_id)
            lot = await svc.get_lot(lot.id, company_id)
            cutting = next(s for s in lot.stages if s.stage_name == "Cutting")
            stitching = next(s for s in lot.stages if s.stage_name == "Making")

            entry = await svc.add_stage_entry(
                cutting.id,
                StageEntryCreate(entry_date=date.today(), pieces_in=0, pieces_out=95, rejected=3, input_weight_kg=Decimal("24.5")),
                user_id,
            )
            lot = await svc.get_lot(lot.id, company_id)
            cutting = next(s for s in lot.stages if s.id == cutting.id)
            stitching = next(s for s in lot.stages if s.id == stitching.id)
            return {
                "lot_colour": lot.colour_id, "entry_in": entry.pieces_in,
                "cut_in": cutting.input_qty, "cut_out": cutting.output_qty, "cut_status": cutting.status,
                "cut_kg": float(cutting.input_weight_kg), "stitching_planned": stitching.planned_qty,
            }
        finally:
            await db.rollback()


def test_cutting_entry_counts_pieces_cut_and_feeds_the_next_stage():
    r = asyncio.run(_run_cutting_entry_scenario())
    assert r["lot_colour"] is None
    assert r["entry_in"] == 98            # 95 good + 3 rejected
    assert (r["cut_in"], r["cut_out"]) == (98, 95)
    assert r["cut_status"] == "in_progress"
    assert r["cut_kg"] == 24.5
    assert r["stitching_planned"] == 95



async def _run_lot_materials_scenario():
    """A new lot's material list is filled from its style: purchased fabric and
    trims by product name, packing by its product, fabric made from yarn
    skipped, unknown names left out. Lines can be added, edited and removed."""
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()

            async def product(kind):
                return (await db.execute(
                    select(Product).where(Product.company_id == company_id, Product.product_type == kind).limit(1)
                )).scalar_one()

            fabric, trim, packing, yarn = await product("fabric"), await product("trim"), await product("packing"), await product("yarn")
            svc = ProductionService(db)
            style = await svc.create_style(
                StyleCreate(
                    name=f"Test Style {uuid4().hex[:8]}", final_output_unit="Pieces", fabric_source="purchased",
                    fabrics=[
                        StyleFabricIn(fabric_name=fabric.name, consumption="0.25", unit="kg"),
                        StyleFabricIn(fabric_name="Knitted In House", consumption="0.1", unit="kg", source_type="yarn"),
                        StyleFabricIn(fabric_name="No Such Fabric", consumption="0.1", unit="kg"),
                    ],
                    trims=[StyleTrimIn(trim_name=trim.name.upper(), quantity=2, unit="pcs")],
                    packing_materials=[StylePackingMaterialIn(material_name="Poly bag", product_id=packing.id, quantity=1)],
                ),
                company_id, user_id,
            )
            lot = await svc.create_lot(ProductionLotCreate(style_id=style.id, planned_qty=100), company_id, user_id)
            filled = {m["product_id"]: m for m in await svc.list_lot_materials(lot.id, company_id)}

            refill_added = await svc.fill_lot_materials_from_style(lot.id, company_id)

            duplicate_error = None
            try:
                await svc.add_lot_material(lot.id, LotMaterialCreate(product_id=trim.id), company_id)
            except BusinessRulesError as e:
                duplicate_error = e.code

            added = await svc.add_lot_material(lot.id, LotMaterialCreate(product_id=yarn.id, planned_qty=Decimal("12.5")), company_id)
            await svc.update_lot_material(added.id, LotMaterialUpdate(planned_qty=Decimal("15")), company_id)
            after_edit = {m["product_id"]: m for m in await svc.list_lot_materials(lot.id, company_id)}
            await svc.delete_lot_material(added.id, company_id)
            after_delete = {m["product_id"] for m in await svc.list_lot_materials(lot.id, company_id)}
            return {
                "fabric": fabric.id, "trim": trim.id, "packing": packing.id, "yarn": yarn.id,
                "filled": filled, "refill_added": refill_added, "duplicate_error": duplicate_error,
                "after_edit": after_edit, "after_delete": after_delete,
            }
        finally:
            await db.rollback()


def test_lot_materials_are_filled_from_the_style_and_editable():
    r = asyncio.run(_run_lot_materials_scenario())
    filled = r["filled"]
    # Purchased fabric, trim (name matched case-insensitively) and packing only.
    assert set(filled) == {r["fabric"], r["trim"], r["packing"]}
    assert float(filled[r["fabric"]]["planned_qty"]) == 25.0     # 0.25 kg x 100 pcs
    assert float(filled[r["trim"]]["planned_qty"]) == 200.0      # 2 x 100 pcs
    assert float(filled[r["fabric"]]["issued_qty"]) == 0
    assert float(filled[r["fabric"]]["balance_qty"]) == 25.0
    assert r["refill_added"] == 0                                # nothing missing the second time
    assert r["duplicate_error"] == "DUPLICATE_MATERIAL"
    assert float(r["after_edit"][r["yarn"]]["planned_qty"]) == 15.0
    assert r["after_delete"] == {r["fabric"], r["trim"], r["packing"]}
