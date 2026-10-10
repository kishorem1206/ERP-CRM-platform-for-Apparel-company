"""
End-to-end realistic test data for the Production module (Phases 1-10) and
a head start on Phase 11's own explicit ask: "Test the complete workflow
using realistic data for a shirt and a trouser, with multiple style parts,
colours, and sizes." Run once, inside the backend container:

    docker exec -it crmplatform-backend-1 python -m scripts.seed_production_pipeline

This is a PERSISTENT seed (no cleanup/rollback) - the lots created here are
meant to stay in the system as real, reviewable demo data. Every name is a
real-sounding garment/customer/material name, never literally "dummy".
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.domain.business_rules import BusinessRulesError
from app.models.production import StylePart
from app.services.production import ProductionService, QuantityValidationError as ProdQtyError
from app.services.sales import SalesService, QuantityValidationError as SalesQtyError
from app.services.inventory import InventoryService
from app.schemas.inventory import ReceiveParams
from app.schemas.production import (
    StyleCreate, StyleSizeIn, StyleColourIn, StylePartColourIn, StylePartSizeIn,
    StyleFabricIn, StyleYarnIn, StyleTrimIn, StylePackingMaterialIn,
    StyleProcessIn, StyleSubProcessIn,
    ProductionLotCreate, LotSizeCreate,
    MaterialIssueCreate, MISItemCreate,
    StageEntryCreate, StageSizeUpdate, StageCreate, StageUpdate,
    StageChallanCreate, StageChallanReceive,
    ProductionOutputCreate, LotAdditionalCostCreate,
)
from app.schemas.sales import SalesOrderCreate, SOItemCreate, DeliveryCreate, DeliveryItemCreate, SalesReturnCreate, SalesReturnItemCreate

COMPANY_ID = UUID("cfa4e79d-ddd7-4c04-8432-d690a97d1b84")
USER_ID = UUID("679a7717-612a-457c-b094-c453572d2b06")

# ── Masters ──────────────────────────────────────────────────────────────────
SIZE = {
    "S": UUID("11f4c15b-1806-4a1c-a850-101502385731"),
    "M": UUID("366ee072-fd10-4373-bad3-4ffed0dac110"),
    "L": UUID("87d7953b-9deb-4742-8144-325d4073d451"),
    "XL": UUID("e5b93a7e-e2c1-402b-a89f-16e4d8bf93aa"),
}
COLOUR = {
    "White": UUID("b290c928-1b09-434f-b7e5-a300fcb95f07"),
    "Navy Blue": UUID("3b90315e-907e-449e-9b9f-db4ae5e1d6b5"),
    "Black": UUID("1f033979-2473-49ea-8a34-60ba4ca6dcc5"),
    "Grey": UUID("375b80d6-a457-4d86-a8b9-d7fa60f2aae5"),
}
UNIT = {
    "kg": UUID("117d0a3e-7bc0-45c3-a78b-22259a036c90"),
    "m": UUID("07d52e97-730f-4ac7-a2aa-37712f067ad1"),
    "pcs": UUID("7857673e-29a9-44be-96c3-95cb7d694a8a"),
    "grs": UUID("a0764e48-4190-4872-aa5f-9ddbf2ead5ed"),
}
CUSTOMER = {
    "Zara India": UUID("bbbbbbbb-0001-0000-0000-000000000001"),
    "H&M Sourcing India": UUID("bbbbbbbb-0001-0000-0000-000000000002"),
    "Myntra Fashion": UUID("bbbbbbbb-0001-0000-0000-000000000004"),
}
WAREHOUSE = {
    "Fabric Store": UUID("0042d444-b26b-4144-a8dc-b34e0eb95497"),
    "Yarn Store": UUID("c8ddc044-5d3f-493c-86e9-d1a31230e336"),
    "Trim Store": UUID("b12fc43e-91bf-4445-af5b-66ded39a6e83"),
    "Packing Store": UUID("80b7f135-ac7f-45ca-b9b2-f7ce13c3371f"),
    "Finished Goods Store": UUID("d8f519bd-30f2-43bc-a55b-0547b46cb343"),
    "Main Warehouse": UUID("52be686a-f9fb-4a56-8682-96997bf8e0db"),
}
VENDOR_SUNRISE = UUID("6630d169-1963-49fd-9a9a-d93d2bd50fe4")  # Sunrise Textile Mills (job_worker)
WORKER_ANITA = UUID("6e3ed77f-ebde-40a3-a328-8214a1205fdc")     # Anita Devi (Tailor)

PRODUCT = {
    "fabric_white_jersey": UUID("cde6451a-6ce6-4f0e-af01-e6c3bbc9aa28"),   # 40sRL S/J White 16" Dia
    "fabric_pink_jersey": UUID("9b652e89-3c4a-4824-8ed6-c79046c88bca"),    # 30sVL S/J Pink 30" Dia
    "yarn_40s_rl": UUID("505b4aef-2c26-4659-a821-b9fc647fd4b0"),
    "yarn_40s_vl": UUID("18715f2e-e5a3-4aaf-8c9d-8a7c3791e9cd"),
    "yarn_30s_rl": UUID("5eea2de2-eb97-41e4-94f1-773050a1cbe2"),
    "button_12mm_white": UUID("52e6398b-ab39-4057-ac83-56cf4b9bad34"),    # unit = grs
    "elastic_20mm": UUID("03eae3e0-18d3-4689-8a5a-78d44416f13e"),         # unit = m
    "bopp_bag": UUID("f7b797da-7716-4e66-8456-207b94fffd6c"),
    "carton": UUID("002ab444-a36f-4f7b-8522-3ba772cc3033"),
    "gusset_bag": UUID("6a4f1619-dad7-42e8-b99c-24520c7438d4"),
}

TODAY = date.today()


async def stock_in(inv: InventoryService, product_id: UUID, warehouse_id: UUID, qty: Decimal, unit_cost: Decimal, unit_id: UUID, notes: str):
    await inv.receive(
        ReceiveParams(
            company_id=COMPANY_ID, product_id=product_id, warehouse_id=warehouse_id,
            quantity=qty, unit_id=unit_id, unit_cost=unit_cost,
            material_type="raw_material", transaction_date=TODAY,
            reference_type="manual", notes=notes,
        ),
        user_id=USER_ID,
    )


async def apply_size_updates(svc: ProductionService, stage, size_specs: dict, company_id: UUID, rework_sizes: set[str] = frozenset()):
    """Reads each size's CURRENT (already-propagated) input_qty straight off
    `stage.sizes` and derives a safe accepted/rejected/[rework] split from it,
    instead of hardcoding numbers that go stale the moment an earlier stage's
    own numbers change — exactly the class of mismatch that update_stage_size's
    own validation (accepted+rejected+rework <= input_qty) is there to catch.
    `size_specs` maps a size key (matching SIZE) to a rejected-qty int; a
    small rework slice is carved out for any key also listed in rework_sizes.
    """
    by_size_id = {s.size_id: s for s in stage.sizes}
    for size_name, rejected in size_specs.items():
        row = by_size_id[SIZE[size_name]]
        rework = max(1, row.input_qty // 50) if size_name in rework_sizes else 0
        accepted = row.input_qty - rejected - rework
        await svc.update_stage_size(stage.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=rework), company_id)


async def ensure_style_part(db, name: str) -> UUID:
    existing = (await db.execute(
        text("SELECT id FROM style_parts WHERE company_id=:c AND name=:n"),
        {"c": str(COMPANY_ID), "n": name},
    )).first()
    if existing:
        return UUID(str(existing[0]))
    part = StylePart(company_id=COMPANY_ID, name=name, created_at=datetime.now(timezone.utc))
    db.add(part)
    await db.flush()
    return part.id


async def scenario_shirt(db):
    print("\n" + "=" * 78)
    print("SCENARIO 1 — SHIRT: Oxford Casual Shirt (Zara India Pvt Ltd)")
    print("=" * 78)
    svc = ProductionService(db)
    sales = SalesService(db)
    inv = InventoryService(db)

    body_part = await ensure_style_part(db, "Body")
    collar_part = await ensure_style_part(db, "Collar")
    cuff_part = await ensure_style_part(db, "Cuff")
    await db.flush()

    style = await svc.create_style(
        StyleCreate(
            name="Oxford Casual Shirt", code="SHIRT-OXFORD-01", garment_type="Shirt",
            gender="Men", season="SS26", final_output_unit="Pieces", pieces_per_box=25,
            fabric_source="purchased", target_price=Decimal("650"),
            sizes=[
                StyleSizeIn(size_id=SIZE["S"], sort_order=1),
                StyleSizeIn(size_id=SIZE["M"], sort_order=2),
                StyleSizeIn(size_id=SIZE["L"], sort_order=3),
            ],
            colours=[StyleColourIn(colour_id=COLOUR["White"], sort_order=1), StyleColourIn(colour_id=COLOUR["Navy Blue"], sort_order=2)],
            part_colours=[
                StylePartColourIn(style_part_id=body_part, colour_id=COLOUR["White"], sort_order=1,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=100), StylePartSizeIn(size_id=SIZE["M"], quantity=250), StylePartSizeIn(size_id=SIZE["L"], quantity=150)]),
                StylePartColourIn(style_part_id=collar_part, colour_id=COLOUR["Navy Blue"], sort_order=2,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=100), StylePartSizeIn(size_id=SIZE["M"], quantity=250), StylePartSizeIn(size_id=SIZE["L"], quantity=150)]),
                StylePartColourIn(style_part_id=cuff_part, colour_id=COLOUR["Navy Blue"], sort_order=3,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=100), StylePartSizeIn(size_id=SIZE["M"], quantity=250), StylePartSizeIn(size_id=SIZE["L"], quantity=150)]),
            ],
            # fabric_source="purchased" + no yarns at all -> "optional yarn planning" case
            fabrics=[StyleFabricIn(fabric_name="Cotton Poplin 120 GSM", source_type="purchased", style_part_id=body_part,
                                    colour_id=COLOUR["White"], consumption=Decimal("0.35"), unit="kg", excess_pct=Decimal("5"), gsm=Decimal("120"))],
            trims=[
                StyleTrimIn(trim_name="Button 12mm White", style_part_id=body_part, quantity=Decimal("8"), unit="pcs", category="Non-Sizable"),
                StyleTrimIn(trim_name="Woven Collar Label", style_part_id=collar_part, quantity=Decimal("1"), unit="pcs", category="Non-Sizable"),
                StyleTrimIn(trim_name="Main Brand Label", quantity=Decimal("1"), unit="pcs", category="Non-Sizable"),
            ],
            packing_materials=[
                StylePackingMaterialIn(material_name="BOPP Bag 8.5x11+2in", product_id=PRODUCT["bopp_bag"], quantity=Decimal("1"), unit="pcs", consumption_stage="During Packing"),
                StylePackingMaterialIn(material_name="Carton 24x18x14in", product_id=PRODUCT["carton"], quantity=Decimal("0.04"), unit="pcs", consumption_stage="During Packing"),
            ],
            processes=[
                StyleProcessIn(seq=1, process_name="Cutting", tolerance_pct=Decimal("3"), input_unit="kg", output_unit="pcs", planned_rate=Decimal("8"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fabric Spreading & Cutting", min_rate=Decimal("7"), max_rate=Decimal("9"), planned_rate=Decimal("8"))]),
                StyleProcessIn(seq=2, process_name="Stitching", tolerance_pct=Decimal("2"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("35"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Collar, Cuff & Main Stitching", min_rate=Decimal("30"), max_rate=Decimal("40"), planned_rate=Decimal("35"))]),
                StyleProcessIn(seq=3, process_name="Final Checking", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("5"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Quality Inspection", min_rate=Decimal("4"), max_rate=Decimal("6"), planned_rate=Decimal("5"))]),
                StyleProcessIn(seq=4, process_name="Packing", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("4"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fold & Pack", min_rate=Decimal("3"), max_rate=Decimal("5"), planned_rate=Decimal("4"))]),
            ],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.flush()
    print(f"Style created: {style.name} ({style.id}), product_id={style.product_id}")

    lot = await svc.create_lot(
        ProductionLotCreate(
            style_id=style.id, customer_id=CUSTOMER["Zara India"], planned_qty=500, colour_id=COLOUR["White"],
            delivery_date=TODAY + timedelta(days=21), season="SS26",
            sizes=[LotSizeCreate(size_id=SIZE["S"], planned_qty=100), LotSizeCreate(size_id=SIZE["M"], planned_qty=250), LotSizeCreate(size_id=SIZE["L"], planned_qty=150)],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    lot_id = lot.id
    print(f"Lot created: {lot.lot_number} ({lot_id}), planned_qty=500 (S100/M250/L150)")

    # ── Stock top-ups (realistic GRN-style receipts before issuing) ────────
    await stock_in(inv, PRODUCT["fabric_white_jersey"], WAREHOUSE["Fabric Store"], Decimal("250"), Decimal("185"), UNIT["kg"], "GRN - Oxford Shirt fabric intake")
    await stock_in(inv, PRODUCT["button_12mm_white"], WAREHOUSE["Trim Store"], Decimal("20"), Decimal("450"), UNIT["grs"], "GRN - buttons (partial, deliberately short for shortage test)")
    await stock_in(inv, PRODUCT["bopp_bag"], WAREHOUSE["Packing Store"], Decimal("600"), Decimal("3.5"), UNIT["pcs"], "GRN - BOPP bags")
    await stock_in(inv, PRODUCT["carton"], WAREHOUSE["Packing Store"], Decimal("25"), Decimal("45"), UNIT["pcs"], "GRN - cartons")
    await db.commit()
    print("Stock topped up: fabric 250kg, buttons 20grs (deliberately short), BOPP 600, cartons 25")

    # ── Material Issue: fabric ──────────────────────────────────────────────
    mis_fabric = await svc.create_mis(
        MaterialIssueCreate(
            production_lot_id=lot_id, warehouse_id=WAREHOUSE["Fabric Store"], issue_date=TODAY,
            notes="Fabric issue for cutting",
            items=[MISItemCreate(product_id=PRODUCT["fabric_white_jersey"], planned_qty=Decimal("183.75"), issued_qty=Decimal("183.75"), unit_id=UNIT["kg"])],
            idempotency_key="shirt-fabric-mis-001",
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"MIS (fabric): {mis_fabric.issue_number}")

    # Duplicate-request test: resend the SAME idempotency key.
    mis_fabric_dup = await svc.create_mis(
        MaterialIssueCreate(
            production_lot_id=lot_id, warehouse_id=WAREHOUSE["Fabric Store"], issue_date=TODAY,
            items=[MISItemCreate(product_id=PRODUCT["fabric_white_jersey"], issued_qty=Decimal("183.75"), unit_id=UNIT["kg"])],
            idempotency_key="shirt-fabric-mis-001",
        ),
        COMPANY_ID, USER_ID,
    )
    assert mis_fabric_dup.id == mis_fabric.id, "idempotency regression: duplicate MIS created a second row"
    print(f"Duplicate-request test OK: resend returned the SAME MIS id ({mis_fabric_dup.id})")

    # ── Missing material / partial stock test: request more buttons than exist ──
    try:
        await svc.create_mis(
            MaterialIssueCreate(
                production_lot_id=lot_id, warehouse_id=WAREHOUSE["Trim Store"], issue_date=TODAY,
                items=[MISItemCreate(product_id=PRODUCT["button_12mm_white"], issued_qty=Decimal("27.78"), unit_id=UNIT["grs"])],
                idempotency_key="shirt-button-mis-attempt1",
            ),
            COMPANY_ID, USER_ID,
        )
        print("FAIL: expected insufficient-stock error for buttons")
    except BusinessRulesError as e:
        print(f"Missing-material test OK: {e.message} (available={e.available}, shortage={e.shortage})")
    await db.rollback()

    # Top up the shortfall for real, then issue successfully.
    await stock_in(inv, PRODUCT["button_12mm_white"], WAREHOUSE["Trim Store"], Decimal("15"), Decimal("450"), UNIT["grs"], "GRN - buttons (topped up after shortage)")
    await db.commit()
    mis_buttons = await svc.create_mis(
        MaterialIssueCreate(
            production_lot_id=lot_id, warehouse_id=WAREHOUSE["Trim Store"], issue_date=TODAY,
            items=[MISItemCreate(product_id=PRODUCT["button_12mm_white"], issued_qty=Decimal("27.78"), unit_id=UNIT["grs"])],
            idempotency_key="shirt-button-mis-002",
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"MIS (buttons, after top-up): {mis_buttons.issue_number}")

    mis_packing = await svc.create_mis(
        MaterialIssueCreate(
            production_lot_id=lot_id, warehouse_id=WAREHOUSE["Packing Store"], issue_date=TODAY,
            items=[
                MISItemCreate(product_id=PRODUCT["bopp_bag"], issued_qty=Decimal("500"), unit_id=UNIT["pcs"]),
                MISItemCreate(product_id=PRODUCT["carton"], issued_qty=Decimal("20"), unit_id=UNIT["pcs"]),
            ],
            idempotency_key="shirt-packing-mis-001",
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"MIS (packing materials): {mis_packing.issue_number}")

    # ── Stage progression ───────────────────────────────────────────────────
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    stages = {s.stage_name: s for s in lot.stages}
    cutting, stitching, checking, packing = stages["Cutting"], stages["Stitching"], stages["Final Checking"], stages["Packing"]

    await svc.add_stage_entry(cutting.id, StageEntryCreate(
        entry_date=TODAY, pieces_in=500, pieces_out=300, rejected=3,
        input_weight_kg=Decimal("110.25"), output_weight_kg=Decimal("105.5"), wastage_kg=Decimal("2.1"), recoverable_kg=Decimal("0.8"),
        operator="Ramesh Kumar", machine="Cutting Table 1",
    ), USER_ID)
    await svc.add_stage_entry(cutting.id, StageEntryCreate(
        entry_date=TODAY + timedelta(days=1), pieces_out=190, rejected=7,
        input_weight_kg=Decimal("73.5"), output_weight_kg=Decimal("69.9"), wastage_kg=Decimal("1.4"), recoverable_kg=Decimal("0.5"),
        operator="Ramesh Kumar", machine="Cutting Table 1",
    ), USER_ID)
    await db.commit()
    print("Cutting: 2 day-wise entries logged (partial completion across 2 days), total out=490, rejected=10, wastage=3.5kg")

    for size_name, qty, accepted, rejected, rework in [("S", 100, 98, 2, 0), ("M", 250, 245, 3, 2), ("L", 150, 147, 2, 1)]:
        await svc.update_stage_size(cutting.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=rework), COMPANY_ID)
    await db.commit()
    print("Cutting: size-wise breakdown recorded (S/M/L) with rejects+rework")

    # Outsourced Stitching -> Sunrise Textile Mills (vendor challan OUT/IN)
    await svc.update_stage(stitching.id, StageUpdate(assignment_type="vendor", vendor_id=VENDOR_SUNRISE, rate_per_pc=Decimal("35")), COMPANY_ID)
    challan = await svc.create_challan(stitching.id, StageChallanCreate(vendor_id=VENDOR_SUNRISE, out_date=TODAY + timedelta(days=2), out_qty=490, expected_return_days=10, notes="Collar/cuff stitching job-work"), COMPANY_ID, USER_ID)
    await db.commit()
    print(f"Stitching: sent OUT 490 pcs to Sunrise Textile Mills (challan {challan.id})")
    challan = await svc.receive_challan(challan.id, StageChallanReceive(in_date=TODAY + timedelta(days=9), in_qty=480, rejected_qty=10, bill_amount=Decimal("16800")), COMPANY_ID)
    await db.commit()
    print(f"Stitching: received IN 480 pcs (10 rejected), bill_amount={challan.bill_amount}")

    lot = await svc.get_lot(lot_id, COMPANY_ID)
    stitching = next(s for s in lot.stages if s.stage_name == "Stitching")
    await apply_size_updates(svc, stitching, {"S": 2, "M": 3, "L": 1}, COMPANY_ID, rework_sizes={"M", "L"})
    await db.commit()

    await svc.add_stage_entry(checking.id, StageEntryCreate(entry_date=TODAY + timedelta(days=10), pieces_in=480, pieces_out=470, rejected=10, operator="QC Team"), USER_ID)
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    checking = next(s for s in lot.stages if s.stage_name == "Final Checking")
    await apply_size_updates(svc, checking, {"S": 2, "M": 4, "L": 4}, COMPANY_ID)
    await db.commit()
    print("Final Checking: 470 passed, 10 rejected, size-wise recorded")

    await svc.add_stage_entry(packing.id, StageEntryCreate(entry_date=TODAY + timedelta(days=11), pieces_in=470, pieces_out=470, operator="Packing Team"), USER_ID)
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    packing = next(s for s in lot.stages if s.stage_name == "Packing")
    await apply_size_updates(svc, packing, {"S": 0, "M": 0, "L": 0}, COMPANY_ID)
    await db.commit()
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    packing = next(s for s in lot.stages if s.stage_name == "Packing")
    final_qty = sum(sz.accepted_qty for sz in packing.sizes)
    print(f"Packing: {final_qty} pcs packed (size-wise total)")

    # Invalid-stage-transition test: try to advance lot status with no stage marked "completed".
    # (advance_lot_status raises before mutating anything, so no rollback needed here.)
    try:
        await svc.advance_lot_status(lot_id, COMPANY_ID, "checking")
        print("UNEXPECTED: lot status advanced without any completed stage")
    except BusinessRulesError as e:
        print(f"Invalid-stage-transition test OK: correctly blocked — {e.message}")

    dispatch_qty = (final_qty * 85) // 100
    output = await svc.create_output(
        ProductionOutputCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Finished Goods Store"], output_date=TODAY + timedelta(days=11),
                                product_id=style.product_id, quantity=Decimal(final_qty), rejected_qty=Decimal("0"),
                                unit_id=UNIT["pcs"], unit_cost=Decimal("310")),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Output received: {output.quantity} pcs @ Finished Goods Store, output_number={output.output_number}")

    await svc.add_lot_additional_cost(lot_id, LotAdditionalCostCreate(cost_type="additional", description="Washing & Pressing Charges", planned_amount=Decimal("15000"), actual_amount=Decimal("14500")), COMPANY_ID)
    await db.commit()

    so = await sales.create_sales_order(
        SalesOrderCreate(customer_id=CUSTOMER["Zara India"], order_date=TODAY,
                          items=[SOItemCreate(product_id=style.product_id, quantity=Decimal(final_qty), unit_id=UNIT["pcs"], unit_price=Decimal("650"), gst_rate=Decimal("5"), hsn_code="6205")]),
        COMPANY_ID, USER_ID, intrastate=True,
    )
    await db.commit()
    so_item_id = so.items[0].id
    # Link the lot to the order it was produced for — order-to-production
    # traceability and the dashboard's dispatch reconciliation both use it.
    await db.execute(text("UPDATE production_lots SET sales_order_id = :so WHERE id = :lot"), {"so": str(so.id), "lot": str(lot_id)})
    await db.commit()
    print(f"Sales Order created: {so.order_number} (linked to the lot)")

    delivery = await sales.create_delivery(
        DeliveryCreate(sales_order_id=so.id, warehouse_id=WAREHOUSE["Finished Goods Store"], delivery_date=TODAY + timedelta(days=12), purpose="sale",
                        items=[DeliveryItemCreate(so_item_id=so_item_id, product_id=style.product_id, lot_id=None, quantity=Decimal(dispatch_qty), unit_id=UNIT["pcs"], unit_price=Decimal("650"), returnable=True, weight_kg=Decimal(dispatch_qty) * Decimal("0.3"))]),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Delivery Challan created: {delivery.delivery_number} ({dispatch_qty} of {final_qty} pcs dispatched to Zara India — partial dispatch)")

    lot_final = await svc.get_lot(lot_id, COMPANY_ID)
    bom = await svc.build_lot_bom(lot_final)
    print(f"BOM check: {bom['total_lines']} lines, {bom['shortage_lines']} short")
    return lot_final.lot_number


async def scenario_trouser(db):
    print("\n" + "=" * 78)
    print("SCENARIO 2 — TROUSER: Slim Fit Chino Trouser (H&M Sourcing India)")
    print("=" * 78)
    svc = ProductionService(db)
    sales = SalesService(db)
    inv = InventoryService(db)

    body_part = await ensure_style_part(db, "Body")
    pocket_part = await ensure_style_part(db, "Pocket Lining")
    waistband_part = await ensure_style_part(db, "Waistband")
    await db.flush()

    style = await svc.create_style(
        StyleCreate(
            name="Slim Fit Chino Trouser", code="TRSR-CHINO-01", garment_type="Trouser",
            gender="Men", season="SS26", final_output_unit="Pieces", pieces_per_box=25,
            fabric_source="yarn", target_price=Decimal("950"),
            sizes=[StyleSizeIn(size_id=SIZE["S"], sort_order=1), StyleSizeIn(size_id=SIZE["M"], sort_order=2), StyleSizeIn(size_id=SIZE["L"], sort_order=3), StyleSizeIn(size_id=SIZE["XL"], sort_order=4)],
            colours=[StyleColourIn(colour_id=COLOUR["Black"], sort_order=1), StyleColourIn(colour_id=COLOUR["Grey"], sort_order=2)],
            part_colours=[
                StylePartColourIn(style_part_id=body_part, colour_id=COLOUR["Black"], sort_order=1,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=80), StylePartSizeIn(size_id=SIZE["M"], quantity=160), StylePartSizeIn(size_id=SIZE["L"], quantity=120), StylePartSizeIn(size_id=SIZE["XL"], quantity=40)]),
                StylePartColourIn(style_part_id=pocket_part, colour_id=COLOUR["Grey"], sort_order=2,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=80), StylePartSizeIn(size_id=SIZE["M"], quantity=160), StylePartSizeIn(size_id=SIZE["L"], quantity=120), StylePartSizeIn(size_id=SIZE["XL"], quantity=40)]),
                StylePartColourIn(style_part_id=waistband_part, colour_id=COLOUR["Black"], sort_order=3,
                                   sizes=[StylePartSizeIn(size_id=SIZE["S"], quantity=80), StylePartSizeIn(size_id=SIZE["M"], quantity=160), StylePartSizeIn(size_id=SIZE["L"], quantity=120), StylePartSizeIn(size_id=SIZE["XL"], quantity=40)]),
            ],
            # Multiple fabrics: body twill + pocket lining.
            fabrics=[
                StyleFabricIn(fabric_name="Cotton Twill 240 GSM", source_type="yarn", style_part_id=body_part, colour_id=COLOUR["Black"],
                              consumption=Decimal("0.55"), unit="kg", excess_pct=Decimal("5"), gsm=Decimal("240")),
                StyleFabricIn(fabric_name="Pocket Lining Poly-Cotton", source_type="purchased", style_part_id=pocket_part, colour_id=COLOUR["Grey"],
                              consumption=Decimal("0.08"), unit="kg", excess_pct=Decimal("4"), gsm=Decimal("120")),
            ],
            yarns=[StyleYarnIn(yarn_name="30s Ring-Spun Lycra Yarn", fabric_index=0, consumption_pct=Decimal("100"), quantity=Decimal("250"), unit="kg")],
            trims=[
                StyleTrimIn(trim_name="Elastic 20mm Waistband", style_part_id=waistband_part, quantity=Decimal("1"), unit="m", category="Non-Sizable"),
                StyleTrimIn(trim_name="Button 12mm White", style_part_id=waistband_part, quantity=Decimal("1"), unit="pcs", category="Non-Sizable"),
                StyleTrimIn(trim_name="Woven Brand Label", quantity=Decimal("1"), unit="pcs", category="Non-Sizable"),
            ],
            packing_materials=[
                StylePackingMaterialIn(material_name="Gusset Bag 5x9.25x2.75in", product_id=PRODUCT["gusset_bag"], quantity=Decimal("1"), unit="pcs", consumption_stage="During Packing"),
                StylePackingMaterialIn(material_name="Carton 24x18x14in", product_id=PRODUCT["carton"], quantity=Decimal("0.04"), unit="pcs", consumption_stage="During Packing"),
            ],
            processes=[
                StyleProcessIn(seq=1, process_name="Cutting", tolerance_pct=Decimal("2"), input_unit="kg", output_unit="pcs", planned_rate=Decimal("9"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fabric Spreading & Cutting", min_rate=Decimal("8"), max_rate=Decimal("10"), planned_rate=Decimal("9"))]),
                StyleProcessIn(seq=2, process_name="Stitching", tolerance_pct=Decimal("2"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("45"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Waistband & Pocket Stitching", min_rate=Decimal("40"), max_rate=Decimal("50"), planned_rate=Decimal("45"))]),
                StyleProcessIn(seq=3, process_name="Final Checking", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("6"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Quality Inspection", min_rate=Decimal("5"), max_rate=Decimal("7"), planned_rate=Decimal("6"))]),
                StyleProcessIn(seq=4, process_name="Packing", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("4"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fold & Pack", min_rate=Decimal("3"), max_rate=Decimal("5"), planned_rate=Decimal("4"))]),
            ],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.flush()
    print(f"Style created: {style.name} ({style.id}), product_id={style.product_id}")

    lot = await svc.create_lot(
        ProductionLotCreate(
            style_id=style.id, customer_id=CUSTOMER["H&M Sourcing India"], planned_qty=400, colour_id=COLOUR["Black"],
            delivery_date=TODAY + timedelta(days=25), season="SS26",
            sizes=[LotSizeCreate(size_id=SIZE["S"], planned_qty=80), LotSizeCreate(size_id=SIZE["M"], planned_qty=160), LotSizeCreate(size_id=SIZE["L"], planned_qty=120), LotSizeCreate(size_id=SIZE["XL"], planned_qty=40)],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    lot_id = lot.id
    print(f"Lot created: {lot.lot_number} ({lot_id}), planned_qty=400 (S80/M160/L120/XL40)")

    await stock_in(inv, PRODUCT["fabric_pink_jersey"], WAREHOUSE["Fabric Store"], Decimal("300"), Decimal("210"), UNIT["kg"], "GRN - Chino Trouser body fabric intake")
    await stock_in(inv, PRODUCT["yarn_30s_rl"], WAREHOUSE["Yarn Store"], Decimal("300"), Decimal("320"), UNIT["kg"], "GRN - lycra yarn top-up")
    await stock_in(inv, PRODUCT["elastic_20mm"], WAREHOUSE["Trim Store"], Decimal("450"), Decimal("12"), UNIT["m"], "GRN - elastic top-up")
    await stock_in(inv, PRODUCT["button_12mm_white"], WAREHOUSE["Trim Store"], Decimal("5"), Decimal("450"), UNIT["grs"], "GRN - buttons top-up")
    await stock_in(inv, PRODUCT["gusset_bag"], WAREHOUSE["Packing Store"], Decimal("450"), Decimal("4"), UNIT["pcs"], "GRN - gusset bags")
    await stock_in(inv, PRODUCT["carton"], WAREHOUSE["Packing Store"], Decimal("60"), Decimal("45"), UNIT["pcs"], "GRN - cartons top-up")
    await db.commit()
    print("Stock topped up: fabric, yarn, elastic, buttons, gusset bags, cartons")

    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Fabric Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["fabric_pink_jersey"], issued_qty=Decimal("231"), unit_id=UNIT["kg"])],
                             idempotency_key="trouser-fabric-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await db.commit()

    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Yarn Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["yarn_30s_rl"], issued_qty=Decimal("231"), unit_id=UNIT["kg"])],
                             idempotency_key="trouser-yarn-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await db.commit()

    # Elastic: issue twice with the same idempotency_key (duplicate-request test).
    mis_elastic = await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Trim Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["elastic_20mm"], issued_qty=Decimal("400"), unit_id=UNIT["m"])],
                             idempotency_key="trouser-elastic-mis-001"),
        COMPANY_ID, USER_ID,
    )
    mis_elastic_dup = await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Trim Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["elastic_20mm"], issued_qty=Decimal("400"), unit_id=UNIT["m"])],
                             idempotency_key="trouser-elastic-mis-001"),
        COMPANY_ID, USER_ID,
    )
    assert mis_elastic.id == mis_elastic_dup.id
    await db.commit()
    print(f"MIS fabric/yarn/elastic issued; duplicate-request test OK on elastic MIS ({mis_elastic.id})")

    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Packing Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["gusset_bag"], issued_qty=Decimal("400"), unit_id=UNIT["pcs"]),
                                    MISItemCreate(product_id=PRODUCT["carton"], issued_qty=Decimal("16"), unit_id=UNIT["pcs"])],
                             idempotency_key="trouser-packing-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await db.commit()

    lot = await svc.get_lot(lot_id, COMPANY_ID)
    stages = {s.stage_name: s for s in lot.stages}
    cutting, stitching, checking, packing = stages["Cutting"], stages["Stitching"], stages["Final Checking"], stages["Packing"]

    # Cutting: weight-based, deliberately landing right at the 2% tolerance boundary.
    await svc.add_stage_entry(cutting.id, StageEntryCreate(
        entry_date=TODAY, pieces_in=400, pieces_out=250, rejected=4,
        input_weight_kg=Decimal("138.6"), output_weight_kg=Decimal("133.0"), wastage_kg=Decimal("4.5"), recoverable_kg=Decimal("1.1"),
        operator="Cutting Team", machine="Cutting Table 2",
    ), USER_ID)
    await svc.add_stage_entry(cutting.id, StageEntryCreate(
        entry_date=TODAY + timedelta(days=1), pieces_out=146, rejected=0,
        input_weight_kg=Decimal("80.0"), output_weight_kg=Decimal("77.5"), wastage_kg=Decimal("1.9"), recoverable_kg=Decimal("0.6"),
        operator="Cutting Team", machine="Cutting Table 2",
    ), USER_ID)
    await db.commit()
    print("Cutting: 2 entries, weight-based (tolerance boundary test — ~2% wastage vs 2% tolerance), total out=396, rejected=4")

    for size_name, accepted, rejected, rework in [("S", 78, 1, 1), ("M", 155, 1, 4), ("L", 118, 1, 1), ("XL", 39, 1, 0)]:
        await svc.update_stage_size(cutting.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=rework), COMPANY_ID)
    await db.commit()

    # Outsourced Stitching -> internal worker Anita Devi (different assignment_type than Scenario 1's vendor).
    await svc.update_stage(stitching.id, StageUpdate(assignment_type="internal_worker", worker_id=WORKER_ANITA, rate_per_pc=Decimal("45")), COMPANY_ID)
    challan = await svc.create_challan(stitching.id, StageChallanCreate(worker_id=WORKER_ANITA, out_date=TODAY + timedelta(days=2), out_qty=390, expected_return_days=12, notes="Waistband & pocket stitching"), COMPANY_ID, USER_ID)
    await db.commit()
    challan = await svc.receive_challan(challan.id, StageChallanReceive(in_date=TODAY + timedelta(days=11), in_qty=385, rejected_qty=5, bill_amount=Decimal("17550")), COMPANY_ID)
    await db.commit()
    print(f"Stitching: outsourced to internal worker Anita Devi — sent 390, received 385, rejected 5, bill_amount={challan.bill_amount}")

    lot = await svc.get_lot(lot_id, COMPANY_ID)
    stitching = next(s for s in lot.stages if s.stage_name == "Stitching")
    await apply_size_updates(svc, stitching, {"S": 1, "M": 2, "L": 1, "XL": 1}, COMPANY_ID, rework_sizes={"M"})
    await db.commit()

    await svc.add_stage_entry(checking.id, StageEntryCreate(entry_date=TODAY + timedelta(days=12), pieces_in=385, pieces_out=375, rejected=10, operator="QC Team"), USER_ID)
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    checking = next(s for s in lot.stages if s.stage_name == "Final Checking")
    await apply_size_updates(svc, checking, {"S": 1, "M": 4, "L": 2, "XL": 1}, COMPANY_ID)
    await db.commit()
    print("Final Checking: 375 passed, 10 rejected, size-wise recorded (with rework earlier in the chain)")

    await svc.add_stage_entry(packing.id, StageEntryCreate(entry_date=TODAY + timedelta(days=13), pieces_in=375, pieces_out=375, operator="Packing Team"), USER_ID)
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    packing = next(s for s in lot.stages if s.stage_name == "Packing")
    await apply_size_updates(svc, packing, {"S": 0, "M": 0, "L": 0, "XL": 0}, COMPANY_ID)
    await db.commit()
    lot = await svc.get_lot(lot_id, COMPANY_ID)
    packing = next(s for s in lot.stages if s.stage_name == "Packing")
    final_qty = sum(sz.accepted_qty for sz in packing.sizes)
    print(f"Packing: {final_qty} pcs packed (size-wise total)")

    dispatch_qty = (final_qty * 90) // 100
    return_qty = min(10, dispatch_qty)
    output = await svc.create_output(
        ProductionOutputCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Finished Goods Store"], output_date=TODAY + timedelta(days=13),
                                product_id=style.product_id, quantity=Decimal(final_qty), rejected_qty=Decimal("0"), unit_id=UNIT["pcs"], unit_cost=Decimal("410")),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Output received: {output.quantity} pcs, output_number={output.output_number}")

    await svc.add_lot_additional_cost(lot_id, LotAdditionalCostCreate(cost_type="additional", description="Garment Dyeing & Finishing Charges", planned_amount=Decimal("22000"), actual_amount=Decimal("21200")), COMPANY_ID)
    await db.commit()

    so = await sales.create_sales_order(
        SalesOrderCreate(customer_id=CUSTOMER["H&M Sourcing India"], order_date=TODAY,
                          items=[SOItemCreate(product_id=style.product_id, quantity=Decimal(final_qty), unit_id=UNIT["pcs"], unit_price=Decimal("950"), gst_rate=Decimal("12"), hsn_code="6203")]),
        COMPANY_ID, USER_ID, intrastate=False,
    )
    await db.commit()
    so_item_id = so.items[0].id
    # Link the lot to the order it was produced for — order-to-production
    # traceability and the dashboard's dispatch reconciliation both use it.
    await db.execute(text("UPDATE production_lots SET sales_order_id = :so WHERE id = :lot"), {"so": str(so.id), "lot": str(lot_id)})
    await db.commit()
    print(f"Sales Order created: {so.order_number} (linked to the lot)")

    delivery = await sales.create_delivery(
        DeliveryCreate(sales_order_id=so.id, warehouse_id=WAREHOUSE["Finished Goods Store"], delivery_date=TODAY + timedelta(days=14), purpose="sale",
                        items=[DeliveryItemCreate(so_item_id=so_item_id, product_id=style.product_id, quantity=Decimal(dispatch_qty), unit_id=UNIT["pcs"], unit_price=Decimal("950"), returnable=True, weight_kg=Decimal(dispatch_qty) * Decimal("0.5"))]),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    delivery_item_id = delivery.items[0].id
    print(f"Delivery Challan created: {delivery.delivery_number} ({dispatch_qty} of {final_qty} pcs dispatched to H&M Sourcing India)")

    sales_return = await sales.create_sales_return(
        SalesReturnCreate(delivery_id=delivery.id, customer_id=CUSTOMER["H&M Sourcing India"], return_date=TODAY + timedelta(days=20), reason="Incorrect waist measurement on a batch of size M",
                           items=[SalesReturnItemCreate(delivery_item_id=delivery_item_id, product_id=style.product_id, quantity=Decimal(return_qty), unit_id=UNIT["pcs"], disposition="usable_stock")]),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Sales Return created: {sales_return.return_number} ({return_qty} pcs returned as usable_stock)")

    lot_final = await svc.get_lot(lot_id, COMPANY_ID)
    bom = await svc.build_lot_bom(lot_final)
    print(f"BOM check: {bom['total_lines']} lines, {bom['shortage_lines']} short")
    return lot_final.lot_number


async def scenario_hoodie(db):
    print("\n" + "=" * 78)
    print("SCENARIO 3 — HOODIE: Heavyweight Fleece Hoodie (Myntra Fashion Pvt Ltd)")
    print("=" * 78)
    svc = ProductionService(db)
    sales = SalesService(db)
    inv = InventoryService(db)

    style = await svc.create_style(
        StyleCreate(
            name="Heavyweight Fleece Hoodie", code="HOOD-FLEECE-01", garment_type="Hoodie",
            gender="Unisex", season="AW26", final_output_unit="Pieces", pieces_per_box=20,
            fabric_source="yarn", target_price=Decimal("1100"),
            sizes=[StyleSizeIn(size_id=SIZE["M"], sort_order=1), StyleSizeIn(size_id=SIZE["L"], sort_order=2), StyleSizeIn(size_id=SIZE["XL"], sort_order=3)],
            colours=[StyleColourIn(colour_id=COLOUR["Grey"], sort_order=1)],
            fabrics=[StyleFabricIn(fabric_name="Fleece 320 GSM", source_type="yarn", colour_id=COLOUR["Grey"], consumption=Decimal("0.5"), unit="kg", excess_pct=Decimal("5"), gsm=Decimal("320"))],
            yarns=[StyleYarnIn(yarn_name="40s Viscose Lycra Fleece Yarn", fabric_index=0, consumption_pct=Decimal("100"), quantity=Decimal("160"), unit="kg")],
            trims=[StyleTrimIn(trim_name="Elastic 20mm Cuff & Hem", quantity=Decimal("0.3"), unit="m", category="Non-Sizable")],
            packing_materials=[StylePackingMaterialIn(material_name="BOPP Bag 8.5x11+2in", product_id=PRODUCT["bopp_bag"], quantity=Decimal("1"), unit="pcs", consumption_stage="During Packing")],
            processes=[
                StyleProcessIn(seq=1, process_name="Cutting", tolerance_pct=Decimal("3"), input_unit="kg", output_unit="pcs", planned_rate=Decimal("10"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fabric Spreading & Cutting", min_rate=Decimal("9"), max_rate=Decimal("11"), planned_rate=Decimal("10"))]),
                StyleProcessIn(seq=2, process_name="Stitching", tolerance_pct=Decimal("2"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("40"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Hood & Body Stitching", min_rate=Decimal("35"), max_rate=Decimal("45"), planned_rate=Decimal("40"))]),
                StyleProcessIn(seq=3, process_name="Final Checking", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("5"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Quality Inspection", min_rate=Decimal("4"), max_rate=Decimal("6"), planned_rate=Decimal("5"))]),
                StyleProcessIn(seq=4, process_name="Packing", tolerance_pct=Decimal("1"), input_unit="pcs", output_unit="pcs", planned_rate=Decimal("4"),
                                sub_processes=[StyleSubProcessIn(seq=1, name="Fold & Pack", min_rate=Decimal("3"), max_rate=Decimal("5"), planned_rate=Decimal("4"))]),
            ],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.flush()
    print(f"Style created: {style.name} ({style.id}), product_id={style.product_id}")

    lot = await svc.create_lot(
        ProductionLotCreate(
            style_id=style.id, customer_id=CUSTOMER["Myntra Fashion"], planned_qty=300, colour_id=COLOUR["Grey"],
            delivery_date=TODAY + timedelta(days=18), season="AW26",
            sizes=[LotSizeCreate(size_id=SIZE["M"], planned_qty=100), LotSizeCreate(size_id=SIZE["L"], planned_qty=150), LotSizeCreate(size_id=SIZE["XL"], planned_qty=50)],
        ),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    lot_id = lot.id
    print(f"Lot created: {lot.lot_number} ({lot_id}), planned_qty=300 (M100/L150/XL50), fully in-house (no outsourcing)")

    await stock_in(inv, PRODUCT["fabric_white_jersey"], WAREHOUSE["Fabric Store"], Decimal("200"), Decimal("185"), UNIT["kg"], "GRN - Hoodie fleece fabric intake")
    await stock_in(inv, PRODUCT["yarn_40s_vl"], WAREHOUSE["Yarn Store"], Decimal("200"), Decimal("340"), UNIT["kg"], "GRN - fleece yarn top-up")
    await stock_in(inv, PRODUCT["elastic_20mm"], WAREHOUSE["Trim Store"], Decimal("150"), Decimal("12"), UNIT["m"], "GRN - elastic top-up")
    await stock_in(inv, PRODUCT["bopp_bag"], WAREHOUSE["Packing Store"], Decimal("350"), Decimal("3.5"), UNIT["pcs"], "GRN - BOPP bags top-up")
    await db.commit()

    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Fabric Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["fabric_white_jersey"], issued_qty=Decimal("157.5"), unit_id=UNIT["kg"])],
                             idempotency_key="hoodie-fabric-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Yarn Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["yarn_40s_vl"], issued_qty=Decimal("157.5"), unit_id=UNIT["kg"])],
                             idempotency_key="hoodie-yarn-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Trim Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["elastic_20mm"], issued_qty=Decimal("90"), unit_id=UNIT["m"])],
                             idempotency_key="hoodie-elastic-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await svc.create_mis(
        MaterialIssueCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Packing Store"], issue_date=TODAY,
                             items=[MISItemCreate(product_id=PRODUCT["bopp_bag"], issued_qty=Decimal("300"), unit_id=UNIT["pcs"])],
                             idempotency_key="hoodie-packing-mis-001"),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print("Material issued: fabric, yarn, elastic, packing — single-pass, happy-path lot")

    lot = await svc.get_lot(lot_id, COMPANY_ID)
    stages = {s.stage_name: s for s in lot.stages}
    cutting, stitching, checking, packing = stages["Cutting"], stages["Stitching"], stages["Final Checking"], stages["Packing"]

    await svc.add_stage_entry(cutting.id, StageEntryCreate(entry_date=TODAY, pieces_in=300, pieces_out=295, rejected=5,
                                                            input_weight_kg=Decimal("157.5"), output_weight_kg=Decimal("152.0"), wastage_kg=Decimal("3.5"), recoverable_kg=Decimal("2.0"),
                                                            operator="Cutting Team", machine="Cutting Table 3"), USER_ID)
    for size_name, accepted, rejected in [("M", 98, 2), ("L", 148, 2), ("XL", 49, 1)]:
        await svc.update_stage_size(cutting.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=0), COMPANY_ID)

    await svc.add_stage_entry(stitching.id, StageEntryCreate(entry_date=TODAY + timedelta(days=1), pieces_in=295, pieces_out=290, rejected=5, operator="Stitching Team"), USER_ID)
    for size_name, accepted, rejected in [("M", 96, 2), ("L", 146, 2), ("XL", 48, 1)]:
        await svc.update_stage_size(stitching.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=0), COMPANY_ID)

    await svc.add_stage_entry(checking.id, StageEntryCreate(entry_date=TODAY + timedelta(days=2), pieces_in=290, pieces_out=285, rejected=5, operator="QC Team"), USER_ID)
    for size_name, accepted, rejected in [("M", 95, 1), ("L", 143, 3), ("XL", 47, 1)]:
        await svc.update_stage_size(checking.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=rejected, rework_qty=0), COMPANY_ID)

    await svc.add_stage_entry(packing.id, StageEntryCreate(entry_date=TODAY + timedelta(days=3), pieces_in=285, pieces_out=285, operator="Packing Team"), USER_ID)
    for size_name, accepted in [("M", 95), ("L", 143), ("XL", 47)]:
        await svc.update_stage_size(packing.id, SIZE[size_name], StageSizeUpdate(accepted_qty=accepted, rejected_qty=0, rework_qty=0), COMPANY_ID)
    await db.commit()
    print("All 4 stages progressed single-pass: Cutting->Stitching->Checking->Packing, 285 pcs through")

    output = await svc.create_output(
        ProductionOutputCreate(production_lot_id=lot_id, warehouse_id=WAREHOUSE["Finished Goods Store"], output_date=TODAY + timedelta(days=3),
                                product_id=style.product_id, quantity=Decimal("285"), rejected_qty=Decimal("15"), unit_id=UNIT["pcs"], unit_cost=Decimal("540")),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Output received: {output.quantity} pcs, output_number={output.output_number}")

    await svc.add_lot_additional_cost(lot_id, LotAdditionalCostCreate(cost_type="additional", description="Brushing & Softening Finish", planned_amount=Decimal("9000"), actual_amount=Decimal("8700")), COMPANY_ID)
    await db.commit()

    so = await sales.create_sales_order(
        SalesOrderCreate(customer_id=CUSTOMER["Myntra Fashion"], order_date=TODAY,
                          items=[SOItemCreate(product_id=style.product_id, quantity=Decimal("285"), unit_id=UNIT["pcs"], unit_price=Decimal("1100"), gst_rate=Decimal("12"), hsn_code="6110")]),
        COMPANY_ID, USER_ID, intrastate=True,
    )
    await db.commit()
    so_item_id = so.items[0].id
    # Link the lot to the order it was produced for — order-to-production
    # traceability and the dashboard's dispatch reconciliation both use it.
    await db.execute(text("UPDATE production_lots SET sales_order_id = :so WHERE id = :lot"), {"so": str(so.id), "lot": str(lot_id)})
    await db.commit()
    print(f"Sales Order created: {so.order_number} (linked to the lot)")

    delivery = await sales.create_delivery(
        DeliveryCreate(sales_order_id=so.id, warehouse_id=WAREHOUSE["Finished Goods Store"], delivery_date=TODAY + timedelta(days=4), purpose="sale",
                        items=[DeliveryItemCreate(so_item_id=so_item_id, product_id=style.product_id, quantity=Decimal("285"), unit_id=UNIT["pcs"], unit_price=Decimal("1100"), returnable=True, weight_kg=Decimal("142.5"))]),
        COMPANY_ID, USER_ID,
    )
    await db.commit()
    print(f"Delivery Challan created: {delivery.delivery_number} (full 285 pcs dispatched to Myntra Fashion — full dispatch, no return)")

    lot_final = await svc.get_lot(lot_id, COMPANY_ID)
    bom = await svc.build_lot_bom(lot_final)
    print(f"BOM check: {bom['total_lines']} lines, {bom['shortage_lines']} short")
    return lot_final.lot_number


async def main():
    async with AsyncSessionLocal() as db:
        lot1 = await scenario_shirt(db)
        lot2 = await scenario_trouser(db)
        lot3 = await scenario_hoodie(db)

        print("\n" + "=" * 78)
        print("DONE. Persistent lots created (visible in the UI, no cleanup performed):")
        print(f"  1. {lot1} — Oxford Casual Shirt — Zara India Pvt Ltd")
        print(f"  2. {lot2} — Slim Fit Chino Trouser — H&M Sourcing India")
        print(f"  3. {lot3} — Heavyweight Fleece Hoodie — Myntra Fashion Pvt Ltd")
        print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
