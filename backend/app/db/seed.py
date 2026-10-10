"""
Seed script: creates initial company, admin user, roles, permissions, and Phase 0 master data.
Run with: python -m app.db.seed
"""
import asyncio
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.core.config import settings
from app.core.security import hash_password

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

PERMISSIONS = [
    "master_data.view", "master_data.create", "master_data.edit", "master_data.delete",
    "crm.view", "crm.create", "crm.edit", "crm.delete",
    "quotation.view", "quotation.create", "quotation.approve", "quotation.cancel",
    "sales_order.view", "sales_order.create", "sales_order.approve", "sales_order.cancel",
    "delivery.view", "delivery.create", "delivery.dispatch",
    "invoice.view", "invoice.create", "invoice.cancel",
    "purchase_order.view", "purchase_order.create", "purchase_order.approve", "purchase_order.cancel",
    "purchase_entry.view", "purchase_entry.create",
    "purchase_return.view", "purchase_return.create",
    "inventory.view", "inventory.receive", "inventory.issue",
    "inventory.transfer", "inventory.adjust", "inventory.opening_balance",
    "inventory.value", "inventory.correct_dates",
    "production.view", "production.create", "production.start", "production.delete",
    "production.log", "production.complete", "production.cancel",
    "finance.view", "finance.receipt", "finance.payment", "finance.expense",
    "reports.sales", "reports.purchase", "reports.inventory",
    "reports.production", "reports.finance", "reports.gst",
    "admin.users", "admin.roles", "admin.settings", "admin.audit",
]


async def seed():
    async with AsyncSessionLocal() as db:
        # ── Company ───────────────────────────────────────────────────────────
        # Re-runs must not create another company (companies has no unique name
        # constraint, so an unconditional INSERT piled up duplicates on every
        # backend start), and must bind to the company that owns the admin user
        # rather than an arbitrary LIMIT 1 row.
        result = await db.execute(text("""
            SELECT c.id FROM companies c
            JOIN users u ON u.company_id = c.id AND u.email = 'admin@company.com'
            ORDER BY c.created_at LIMIT 1
        """))
        company_id = result.scalar()
        if company_id is None:
            company_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO companies (id, name, currency, default_hsn, state_code, created_at, updated_at)
                    VALUES (:id, :name, :currency, :hsn, :state_code, now(), now())
                """),
                {"id": company_id, "name": "My Apparel Company",
                 "currency": "INR", "hsn": "6111", "state_code": 29},
            )
        company_id = str(company_id)

        # ── Permissions ───────────────────────────────────────────────────────
        for code in PERMISSIONS:
            await db.execute(
                text("""
                    INSERT INTO permissions (id, code)
                    VALUES (:id, :code)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid.uuid4()), "code": code},
            )

        # ── Administrator role ────────────────────────────────────────────────
        role_result = await db.execute(
            text("SELECT id FROM roles WHERE company_id = :c AND name = 'Administrator'"),
            {"c": company_id},
        )
        existing_role = role_result.scalar()
        if not existing_role:
            role_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO roles (id, company_id, name, is_system)
                    VALUES (:id, :company_id, 'Administrator', true)
                    ON CONFLICT DO NOTHING
                """),
                {"id": role_id, "company_id": company_id},
            )
        else:
            role_id = str(existing_role)

        # Assign all permissions to the admin role
        perms = await db.execute(text("SELECT id FROM permissions"))
        for (perm_id,) in perms.fetchall():
            await db.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p) ON CONFLICT DO NOTHING"),
                {"r": role_id, "p": str(perm_id)},
            )

        # ── Admin user ────────────────────────────────────────────────────────
        user_result = await db.execute(
            text("SELECT id FROM users WHERE company_id = :c AND email = 'admin@company.com'"),
            {"c": company_id},
        )
        existing_user = user_result.scalar()
        if not existing_user:
            user_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO users (id, company_id, email, hashed_password, full_name, is_active, is_owner)
                    VALUES (:id, :company_id, :email, :pwd, :name, true, true)
                    ON CONFLICT DO NOTHING
                """),
                {"id": user_id, "company_id": company_id, "email": "admin@company.com",
                 "pwd": hash_password(os.environ["ADMIN_SEED_PASSWORD"]), "name": "System Administrator"},
            )
            await db.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r) ON CONFLICT DO NOTHING"),
                {"u": user_id, "r": role_id},
            )

        # ── Units ─────────────────────────────────────────────────────────────
        for abbr, name, utype in [
            ("kg", "Kilogram", "weight"),
            ("g", "Gram", "weight"),
            ("m", "Metre", "length"),
            ("cm", "Centimetre", "length"),
            ("pcs", "Pieces", "piece"),
            ("dzn", "Dozen", "piece"),
            ("grs", "Gross", "piece"),
            ("roll", "Roll", "piece"),
            ("set", "Set", "piece"),
        ]:
            await db.execute(
                text("""
                    INSERT INTO units (id, company_id, name, abbreviation, unit_type)
                    VALUES (:id, :company_id, :name, :abbr, :utype)
                    ON CONFLICT (company_id, abbreviation) DO NOTHING
                """),
                {"id": str(uuid.uuid4()), "company_id": company_id,
                 "name": name, "abbr": abbr, "utype": utype},
            )

        # ── Process Master ───────────────────────────────────────────────────
        for i, proc_name in enumerate([
            "Knitting", "Dyeing", "Compacting", "Printing", "Cutting", "Making",
            "Fusing", "Stitching", "Trimming", "Checking", "Ironing", "Packing",
        ]):
            await db.execute(
                text("""
                    INSERT INTO process_masters (id, company_id, name, sort_order)
                    VALUES (:id, :company_id, :name, :sort_order)
                    ON CONFLICT (company_id, name) DO NOTHING
                """),
                {"id": str(uuid.uuid4()), "company_id": company_id,
                 "name": proc_name, "sort_order": i},
            )

        # ── Warehouses ────────────────────────────────────────────────────────
        for wh_name, wh_code in [
            ("Main Warehouse", "WH-MAIN"),
            ("Yarn Store", "WH-YARN"),
            ("Fabric Store", "WH-FAB"),
            ("Trim Store", "WH-TRIM"),
            ("Packing Store", "WH-PACK"),
            ("Finished Goods Store", "WH-FG"),
            ("Rejection Store", "WH-REJ"),
        ]:
            await db.execute(
                text("""
                    INSERT INTO warehouses (id, company_id, name, code, is_active)
                    VALUES (:id, :company_id, :name, :code, true)
                    ON CONFLICT (company_id, code) DO NOTHING
                """),
                {"id": str(uuid.uuid4()), "company_id": company_id,
                 "name": wh_name, "code": wh_code},
            )

        # ── Document sequences ────────────────────────────────────────────────
        for doc_type, prefix in [
            ("purchase_order", "PO"), ("purchase_entry", "GRN"), ("purchase_return", "PRN"),
            ("sales_order", "SO"), ("quotation", "QT"), ("invoice", "INV"),
            ("delivery", "DEL"), ("credit_note", "CN"), ("stock_transfer", "STT"),
            ("stock_adjustment", "ADJ"), ("production_lot", "LOT"),
            ("material_issue", "MIS"), ("production_entry", "PE"),
            ("job_work_challan", "JWC"),
        ]:
            await db.execute(
                text("""
                    INSERT INTO document_sequences (company_id, document_type, prefix, separator, year_format, next_number, padding)
                    VALUES (:c, :dt, :prefix, '/', 'YY', 1, 4)
                    ON CONFLICT (company_id, document_type) DO NOTHING
                """),
                {"c": company_id, "dt": doc_type, "prefix": prefix},
            )

        await db.commit()

        # ── Phase 0: Categories, Colours, Sizes, Products ─────────────────────
        await _seed_phase0(db, company_id)

        await db.commit()
        print("✓ Seed complete")
        print(f"  Company ID : {company_id}")
        print("  Admin user : admin@company.com / <password you set in ADMIN_SEED_PASSWORD>")


async def _seed_phase0(db: AsyncSession, company_id: str) -> None:
    """Phase 0 master data: categories, colours, sizes, products."""

    # ── Categories ────────────────────────────────────────────────────────────
    categories = ["Yarn", "Fabric", "Trim", "Packing Material", "Finished Goods"]
    for cat_name in categories:
        await db.execute(
            text("INSERT INTO categories (id, company_id, name) VALUES (:id, :c, :n) ON CONFLICT (company_id, name) DO NOTHING"),
            {"id": str(uuid.uuid4()), "c": company_id, "n": cat_name},
        )

    # ── Sub-categories ────────────────────────────────────────────────────────
    sub_cats = [
        ("Yarn", "Viscose Lycra Yarn"), ("Yarn", "Ring Lycra Yarn"),
        ("Fabric", "Single Jersey"), ("Fabric", "Double Jersey"), ("Fabric", "Rib Fabric"),
        ("Trim", "Buttons"), ("Trim", "Elastic"), ("Trim", "Zipper"), ("Trim", "Label"),
        ("Packing Material", "Inner Card"), ("Packing Material", "Poly Bag"), ("Packing Material", "Carton"),
    ]
    for cat_name, sub_name in sub_cats:
        await db.execute(
            text("""
                INSERT INTO sub_categories (id, company_id, category_id, name)
                SELECT :id, :c, cat.id, :sub
                FROM categories cat WHERE cat.company_id = :c AND cat.name = :cat
                ON CONFLICT DO NOTHING
            """),
            {"id": str(uuid.uuid4()), "c": company_id, "sub": sub_name, "cat": cat_name},
        )

    # ── Colours ───────────────────────────────────────────────────────────────
    colours = [
        ("White", "#FFFFFF"), ("Black", "#000000"), ("Pink", "#FFC0CB"),
        ("Navy Blue", "#001F5B"), ("Red", "#CC0000"), ("Grey", "#808080"),
        ("Brown", "#795548"), ("Yellow", "#FFEB3B"), ("Green", "#2E7D32"),
        ("Orange", "#E65100"),
    ]
    for col_name, hex_code in colours:
        await db.execute(
            text("INSERT INTO colours (id, company_id, name, hex_code) VALUES (:id, :c, :n, :h) ON CONFLICT (company_id, name) DO NOTHING"),
            {"id": str(uuid.uuid4()), "c": company_id, "n": col_name, "h": hex_code},
        )

    # ── Sizes ─────────────────────────────────────────────────────────────────
    sizes = [("XS", 1), ("S", 2), ("M", 3), ("L", 4), ("XL", 5), ("XXL", 6), ("XXXL", 7),
             ("3M", 10), ("6M", 11), ("9M", 12), ("12M", 13), ("18M", 14), ("24M", 15)]
    for sz_name, sort in sizes:
        await db.execute(
            text("INSERT INTO sizes (id, company_id, name, sort_order) VALUES (:id, :c, :n, :s) ON CONFLICT (company_id, name) DO NOTHING"),
            {"id": str(uuid.uuid4()), "c": company_id, "n": sz_name, "s": sort},
        )

    await db.flush()

    # ── Look up IDs for FK references ─────────────────────────────────────────
    unit_ids = {}
    for (abbr, uid) in (await db.execute(
        text("SELECT abbreviation, id FROM units WHERE company_id = :c"), {"c": company_id}
    )).fetchall():
        unit_ids[abbr] = str(uid)

    hsn_ids = {}
    for (hsn, uid) in (await db.execute(text("SELECT hsn, id FROM hsn_codes"))).fetchall():
        hsn_ids[hsn] = str(uid)

    cat_ids = {}
    for (name, uid) in (await db.execute(
        text("SELECT name, id FROM categories WHERE company_id = :c"), {"c": company_id}
    )).fetchall():
        cat_ids[name] = str(uid)

    sub_cat_ids = {}
    for (name, uid) in (await db.execute(
        text("SELECT sc.name, sc.id FROM sub_categories sc JOIN categories c ON sc.category_id = c.id WHERE c.company_id = :cid"),
        {"cid": company_id}
    )).fetchall():
        sub_cat_ids[name] = str(uid)

    # ── Products ──────────────────────────────────────────────────────────────
    products = [
        # code, name, type, unit_abbr, hsn, category, sub_category, fabric_type, fabric_composition, gsm, construction
        ("YARN-30S-VL", "30s VL - Viscose Lycra Yarn 30 Count", "yarn", "kg", "5509", "Yarn", "Viscose Lycra Yarn", None, None, None, None),
        ("YARN-30S-RL", "30s RL - Ring Lycra Yarn 30 Count",    "yarn", "kg", "5509", "Yarn", "Ring Lycra Yarn",    None, None, None, None),
        ("YARN-40S-VL", "40s VL - Viscose Lycra Yarn 40 Count", "yarn", "kg", "5509", "Yarn", "Viscose Lycra Yarn", None, None, None, None),
        ("YARN-40S-RL", "40s RL - Ring Lycra Yarn 40 Count",    "yarn", "kg", "5509", "Yarn", "Ring Lycra Yarn",    None, None, None, None),
        ("FAB-30VL-SJ-PNK-30", "30sVL S/J Pink 30\" Dia",  "fabric", "kg", "6006", "Fabric", "Single Jersey", "Single Jersey", "30s Viscose Lycra", 160.00, "S/J - 30\" dia"),
        ("FAB-40RL-SJ-WHT-16", "40sRL S/J White 16\" Dia", "fabric", "kg", "6006", "Fabric", "Single Jersey", "Single Jersey", "40s Ring Lycra",    180.00, "S/J - 16\" dia"),
        ("TRIM-BTN-12MM-WHT", "Button 12mm White",       "trim", "grs", "9606", "Trim", "Buttons", None, None, None, None),
        ("TRIM-BTN-10MM-BRN", "Button 10mm Brown",       "trim", "grs", "9606", "Trim", "Buttons", None, None, None, None),
        ("TRIM-ELS-35MM-LYC", "Elastic 35mm Lycra",      "trim", "m",   "5806", "Trim", "Elastic", None, None, None, None),
        ("TRIM-ELS-20MM-3WF", "Elastic 20mm 3 Weft",     "trim", "m",   "5806", "Trim", "Elastic", None, None, None, None),
        ("PACK-ICARD-7.5X11",  'Inner Card 7.5"x11"',               "packing", "pcs", "4823", "Packing Material", "Inner Card", None, None, None, None),
        ("PACK-BOPP-8.5X11P2", 'BOPP Bag 8.5"x11"+2"',              "packing", "pcs", "3923", "Packing Material", "Poly Bag",   None, None, None, None),
        ("PACK-GASET-5X9.25",  'Gusset Bag 5*9.25*2.75 flap+1.75"', "packing", "pcs", "3923", "Packing Material", "Poly Bag",   None, None, None, None),
        ("PACK-CTN-24X18X14",  'Carton 24"x18"x14"',                "packing", "pcs", "4819", "Packing Material", "Carton",     None, None, None, None),
        ("SK-203-50", "Style SK-203-50", "finished_good", "pcs", "6109", "Finished Goods", None, None, None, None, None),
        ("SK-245-50", "Style SK-245-50", "finished_good", "pcs", "6109", "Finished Goods", None, None, None, None, None),
        ("IC-2",      "Style IC-2",      "finished_good", "pcs", "6111", "Finished Goods", None, None, None, None, None),
        ("IC-338",    "Style IC-338",    "finished_good", "pcs", "6111", "Finished Goods", None, None, None, None, None),
    ]

    for (code, name, ptype, unit_abbr, hsn, cat, sub_cat, fabric_type, fabric_comp, gsm, construction) in products:
        prod_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, sub_category_id,
                                      fabric_type, fabric_composition, gsm, construction, is_active, created_at, updated_at)
                VALUES (:id, :c, :code, :name, :ptype,
                        :unit_id, :hsn_id, :cat_id, :sub_cat_id,
                        :fabric_type, :fabric_comp, :gsm, :construction,
                        true, NOW(), NOW())
                ON CONFLICT (company_id, code) DO NOTHING
            """),
            {
                "id": prod_id, "c": company_id, "code": code, "name": name, "ptype": ptype,
                "unit_id": unit_ids.get(unit_abbr), "hsn_id": hsn_ids.get(hsn),
                "cat_id": cat_ids.get(cat), "sub_cat_id": sub_cat_ids.get(sub_cat) if sub_cat else None,
                "fabric_type": fabric_type, "fabric_comp": fabric_comp,
                "gsm": gsm, "construction": construction,
            },
        )

    await db.flush()

    # ── Style variants ────────────────────────────────────────────────────────
    sk_sizes = ["S", "M", "L", "XL", "XXL"]
    ic_sizes = ["3M", "6M", "9M", "12M", "18M", "24M"]

    size_ids = {}
    for (sz, uid) in (await db.execute(
        text("SELECT name, id FROM sizes WHERE company_id = :c"), {"c": company_id}
    )).fetchall():
        size_ids[sz] = str(uid)

    for style_code, size_list in [("SK-203-50", sk_sizes), ("SK-245-50", sk_sizes),
                                    ("IC-2", ic_sizes), ("IC-338", ic_sizes)]:
        prod_result = await db.execute(
            text("SELECT id FROM products WHERE company_id = :c AND code = :code"),
            {"c": company_id, "code": style_code},
        )
        prod_id = prod_result.scalar()
        if not prod_id:
            continue
        for sz in size_list:
            sz_id = size_ids.get(sz)
            if not sz_id:
                continue
            await db.execute(
                text("""
                    INSERT INTO product_variants (id, product_id, sku, size_id, is_active)
                    VALUES (:id, :prod, :sku, :sz, true)
                    ON CONFLICT DO NOTHING
                """),
                {"id": str(uuid.uuid4()), "prod": str(prod_id),
                 "sku": f"{style_code}-{sz}", "sz": sz_id},
            )


if __name__ == "__main__":
    asyncio.run(seed())
