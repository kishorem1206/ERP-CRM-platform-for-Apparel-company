# ERP Upgrade Progress

Generated: 2026-08-29

---

## Phase 0 — Audit ✅ Complete

**Completed:** 2026-08-29

### What was done
- Full codebase audit: all DB tables, ORM models, API endpoints, frontend pages
- Identified schema drift: `material_composition_items`, `fabric_variants`, `trim_variants` existed only in ORM (not in Alembic migrations)
- Confirmed `inventory_lots` has `bags`, `kg_per_bag`, `trim_type`, `trim_unit`, `split_by_colour`, `split_by_dia` in the actual DB but not in migrations
- Output: `docs/ERP_UPGRADE_AUDIT.md` — complete gap analysis

---

## Phase 1 — Schema Drift Fix + Inventory Booking + Lot Browser ✅ Complete

**Completed:** 2026-08-29

### What was done

#### 1. Migration 003 — Schema Drift Remediation
- Created `backend/alembic/versions/003_materials_tables.py`
- DDL uses IF NOT EXISTS guards (safe on any DB state)
- Adds: `bags`, `kg_per_bag`, `trim_type`, `trim_unit`, `split_by_colour`, `split_by_dia`, `notes` columns to `inventory_lots`
- Creates: `material_composition_items`, `fabric_variants`, `trim_variants` tables with proper FKs
- Seeds: yarn/fabric/trim/fabric_run document sequences via ON CONFLICT DO NOTHING
- Applied via psql — all confirmed (IF NOT EXISTS NOTICEs for existing objects; no errors)

#### 2. Verified Existing Systems
- `document_sequences` — all 4 material types (yarn/FAB/TRM/FR) already seeded ✅
- Celery task `refresh_inventory_balance` — exists at `backend/app/workers/tasks.py:18` ✅
- `inventory_balance` materialized view — exists in DB ✅
- Inventory booking logic in `MaterialsService` — already wired (fires when warehouse_id + product_id + unit_id all present) ✅

#### 3. Inventory Booking — Frontend Wired
Added "Book to Inventory" section to all three Add modals:

- **`AddYarnModal.tsx`** — warehouse, product (type=yarn), unit dropdowns; quantity = bags × kg_per_bag auto-calculated; confirmation message shows total kg
- **`AddFabricModal.tsx`** — warehouse, product (type=fabric), quantity, unit dropdowns; confirmation message on save
- **`AddTrimsModal.tsx`** — warehouse, product (type=trim), unit dropdowns; confirmation message shows quantity

All three modals now pass `warehouse_id`, `product_id`, `unit_id` (and `quantity` for fabric/trim) to the POST endpoint. Booking is optional — selecting "— Skip —" warehouse leaves them unset and the backend skips the transaction.

Dropdowns populate from:
- Warehouses: `GET /master/warehouses`
- Units: `GET /master/units`
- Products: `GET /products?product_type={yarn|fabric|trim}`

#### 4. Lot Browser — `/inventory/lots`
- New page at `frontend/src/app/(app)/inventory/lots/page.tsx`
- Filter tabs: All / Yarn / Fabric / Trims
- Client-side search on lot number, composition, yarn count, construction, trim type
- Colour-coded type badges (amber/blue/purple)
- Row click → lot detail page
- Paginated (server-side, 50/page)
- Added "Material Lots" quick link on Inventory index page

#### 5. Lot Detail — `/inventory/lots/[id]`
- New page at `frontend/src/app/(app)/inventory/lots/[id]/page.tsx`
- Renders appropriate section per material type (yarn / fabric / trim)
- Shows: specification fields, fibre composition pills, fabric/trim variants table, purchase details, notes
- Yarn: calculates total kg (bags × kg/bag) and total value
- Clean back-navigation, loading and 404 states

---

---

## Phase 2 — Create Workflow Shell ✅ Complete

**Completed:** 2026-08-30

### What was found
Phase 2 was already substantially implemented from prior work. The full Create shell existed:
- `Sidebar` — "Create" button (primary, full-width, Plus icon) at top of nav
- `CreateMenu` — Quick Create panel (positioned below Create button, backdrop-blurred overlay, X to close)
  - **Production** section: New Lot, New Fabric Run
  - **Stock** section: Add Yarn, Add Fabric, Add Trims
- `ModalShell` — Scrollable modal wrapper used by all 5 forms
- `Field`, `Input`, `Select`, `Textarea`, `SegControl`, `ModalActions` — complete reusable form component set

### What was fixed/added
- **Escape key handler** added to `ModalShell` — closes the active form modal on Escape
- **Escape key handler** added to `CreateMenu` — closes the Quick Create panel on Escape

### Test results (Playwright headless)
- ✅ Login + Dashboard loaded
- ✅ Create menu opens with correct sections (PRODUCTION / STOCK)
- ✅ New Lot → "New Production Lot" modal opens, closes on Escape
- ✅ New Fabric Run → "New Fabric Run" modal opens, closes on Escape
- ✅ Add Yarn → "Add Yarn" modal opens, closes on Escape
- ✅ Add Fabric → "Add Fabric" modal opens, closes on Escape
- ✅ Add Trims → "Add Trims" modal opens, closes on Escape
- ✅ Dimmed backdrop visible, rounded corners, matches existing design language

---

## Phase 3 — New Lot Workflow ✅ Complete

**Completed:** 2026-08-30

### What was done

#### 1. Backend — Concurrency-Safe Lot Number Generation
- Replaced `_next_seq` (COUNT(*)+1 race) with `_next_lot_number` using `document_sequences` SELECT FOR UPDATE
- Mapped `year_format` strings ("YY"→`%y`, "YYYY"→`%Y`) to correct strftime codes; format now `LOT/26/0001`
- Sequence increments only on commit; FK/UNIQUE failures roll it back automatically

#### 2. Schema — Optional Manual Lot Number
- Added `lot_number: str | None = None` to `ProductionLotCreate`
- Service: uses user-provided lot_number if non-empty, otherwise auto-generates
- UNIQUE constraint `(company_id, lot_number)` already existed in DB — enforced at DB level

#### 3. Duplicate Prevention — Proper 409 Response
- Added `IntegrityError` catch in `create_lot` endpoint
- UNIQUE violation → 409 "Lot number already exists"
- FK violation (invalid style/customer) → 422 "Invalid reference"

#### 4. Frontend — Lot Number Field Added
- `NewLotModal.tsx`: added optional "Lot Number" input with hint "Leave blank to auto-generate (e.g. LOT/0001)"
- Payload sends `lot_number` only when user provides a value (non-empty string)
- Subtitle updated: "Start a new lot linked to a style."

### Test results (actual HTTP calls against running backend)
- ✅ Auto-generated lot number: `LOT/26/0001` format, sequence increments correctly
- ✅ Manual lot number: user-provided number used verbatim
- ✅ Duplicate lot number: returns 409 with clear message
- ✅ Unauthorized request (no token): returns 401
- ✅ Lot with valid style: `style_name` populated in response
- ✅ Lot with invalid style UUID: returns 422 (FK violation, no partial data created)
- ✅ Rollback: failed creation (IntegrityError) does NOT increment sequence
- ✅ Persistence: all created lots visible in `GET /production/lots`
- ✅ Second auto-generated lot: sequence advanced correctly (LOT/26/0002, LOT/26/0003…)

---

## Phases 4–16 — Pending

See `docs/UPGRADE.md` for the full 16-phase plan.
