# Apparel ERP — Build Progress

## Status: All 18 Phases Complete ✅

---

## Completed Phases

### Phase 0 — Seed / Master Data
Real inventory data seeded into the database via `backend/app/db/seed.py`.

**Products seeded:**
- **Yarn (4):** 30s VL, 30s RL, 40s VL, 40s RL
- **Fabric (2):** 30sVL-S/J-Pink-30, 40sRL-S/J-White-16
- **Trims (4):** Button-12mm-White, Button-10mm-Brown, Elastic-35mm-Lycra, Elastic-20mm-3Weft
- **Packing (4):** InnerCard-7.5"x11, BOPP-8.5"x11"+2, Gaset-5*9.25*2.75flap+1.75, Carton-24"18"14"
- **Finished Goods (4):** SK-203-50, SK-245-50, IC-2, IC-338
  - SK styles → variants: S / M / L / XL / XXL
  - IC styles → variants: 3M / 6M / 9M / 12M / 18M / 24M

**Master data seeded:**
- 1 company, 1 admin user (`admin@company.com` / `Admin@1234`)
- 58 permissions → 1 Administrator role
- 9 units, 6 warehouses, 13 document sequences
- 5 categories, 12 sub-categories, 10 colours, 13 sizes
- HSN codes (6111, 5509, 5510, 5205, 6001, 3923, 4819, 4823, 9606)

---

### Phase 1 — Product Document
`PRODUCT.md` — full 18-phase product spec, architecture decisions, agent design, RBAC model, GST engine design, and data model overview.

---

### Phase 2 — Database
- PostgreSQL schema: `db/schema.sql` — all core tables including companies, users, roles, permissions, products, variants, inventory_transactions, purchase orders, sales orders, production lots, invoices, GST entries, notifications, refresh_tokens, file_attachments, audit_log, etc.
- Seed SQL files: `002_permissions.sql`, `003_hsn_codes.sql`, `004_master_data.sql`, `005_products.sql`
- Python seed runner: `backend/app/db/seed.py` (idempotent)
- Docker postgres mapped on **port 5433** (5432 occupied by system postgres)

---

### Phase 3 — Backend (FastAPI)
Full async FastAPI application at `backend/`.

**Core infrastructure:**
- `app/core/config.py` — pydantic-settings, multi-path `.env` discovery
- `app/core/security.py` — bcrypt hashing, JWT access tokens (15 min), refresh tokens (30 days), TOTP, OTP, rate-limit helper, 2FA session management
- `app/db/session.py` — asyncpg + SQLAlchemy 2.x async engine, session-per-request
- `app/api/v1/deps.py` — `DBSession`, `AuthUser` (JWT decode + RBAC), `require_permission()`

**Models:** Company, User, Role, Permission, UserRole, RolePermission, RefreshToken, Unit, Category, SubCategory, Brand, Colour, Size, HsnCode, Warehouse, Product, ProductVariant, FileAttachment, InventoryTransaction, Notification + all domain models

**Key endpoints:**
- `POST /api/v1/auth/login` — JWT login with rate limiting + account lockout
- `POST /api/v1/auth/logout` — refresh token revocation
- `GET  /api/v1/auth/me`
- `GET  /api/v1/health`
- Full product CRUD, master data, all module endpoints (see per-phase detail below)

---

### Phase 4 — Frontend (Next.js 14)
App shell at `frontend/` with Tailwind CSS + shadcn-style design tokens.

**Pages built:**
- `/login` — React Hook Form + Zod, JWT stored in localStorage, 2FA step, "Forgot password?" link
- `/dashboard` — 6-KPI grid (Revenue MTD, Outstanding, Open Orders, Active Lots, Stock Value, Low Stock)
- `/inventory` — Quick-links + warehouse stock summary cards
- All module pages (see per-phase detail below)

**Shared components:** `KpiCard`, `DataTable`, `StatusBadge`
**Layout:** `Sidebar` (11-module nav incl. Security), `Topbar` (notification bell + WebSocket)
**API client:** `src/lib/api.ts` — axios with JWT interceptor + silent refresh

---

### Phase 5 — Unit Tests
`tests/unit/` — pytest-asyncio, 17+ tests covering:
- `test_business_rules.py` — stock issue, warehouse transfer, SOD, financial deletion, quotation conversion, material variance
- `test_pricing.py` — cost sheet, zero margin, Decimal enforcement
- `test_security.py` — bcrypt hash/verify, JWT decode, expiry, tamper detection, token type validation

---

### Phase 6 — Integration Tests
`tests/integration/` — real asyncpg database, session-scoped schema create/drop:
- `test_auth.py` — login success/fail, lockout after 5 attempts, refresh flow, protected route
- `test_inventory_ledger.py` — receive (+1 transaction), over-issue (422), transfer math, immutability

---

### Phase 7 — Docker
Full containerised stack:
- `backend/Dockerfile` — python:3.13-slim, non-root user, HEALTHCHECK
- `frontend/Dockerfile` — multi-stage (deps → builder → runner on node:20-alpine), standalone output
- `nginx/nginx.conf` — reverse proxy: `/api/` → FastAPI, `/ws/` → WebSocket, `/` → Next.js
- `docker-compose.yml` — postgres (5433), redis (password-authenticated), backend, celery_worker, celery_beat, frontend, nginx
- Per-context `.dockerignore` files for backend and frontend build contexts

---

### Phase 8 — Purchase Module
Full purchase cycle: vendor master → purchase orders → goods receipt → inventory update.

- `models/purchase.py` — Vendor, VendorContact, VendorBankDetail, PurchaseOrder, PurchaseOrderItem, PurchaseEntry, PurchaseEntryItem
- `services/purchase.py` — GST line-item arithmetic, PO lifecycle (draft → approved → partial/received/cancelled), GRN creation calling `InventoryService.receive()` per item
- 13 endpoints under `/api/v1/purchase/`
- Frontend: purchasing hub, vendor list, PO list, GRN list

---

### Phase 9 — Sales Module
Full sales cycle: Customer → Quotation → Sales Order → Delivery Challan → Invoice.

- `models/sales.py` — Customer, CustomerAddress, CustomerContact, PriceList, PriceListItem, Quotation, QuotationItem, SalesOrder, SalesOrderItem, Delivery, DeliveryItem, Invoice
- `services/sales.py` — GST arithmetic, quotation lifecycle, SO creation, delivery dispatch calling `InventoryService.issue()`, invoice generation
- 22 endpoints under `/api/v1/sales/`
- Frontend: CRM hub, customer list, quotations, SOs, deliveries, invoices

---

### Phase 10 — Production Module
Full production cycle: Styles → Production Lots → Stages → Material Issues → Output.

- `models/production.py` — Style, ProductionLot, ProductionLotSize, ProductionStage, ProductionStageEntry, MaterialIssue, MaterialIssueItem, ProductionOutput
- `services/production.py` — lot creation with 5 auto-default stages, MIS creation calling `InventoryService.issue()`, output creation calling `InventoryService.receive()` for FG
- 14 endpoints under `/api/v1/production/`
- Frontend: production hub, lot list, MIS list, output list

---

### Phase 11 — Finance Module
Payments, credit/debit notes, party ledger, and GST register.

- `models/finance.py` — Payment, PaymentAllocation, VendorPayment, VendorPaymentAllocation, CreditNote, DebitNote
- `services/finance.py` — payment creation updates invoice balances; running balance ledger; GSTR-1 output and GSTR-2A input registers
- 14 endpoints under `/api/v1/finance/`
- Frontend: finance hub, payments, vendor payments, credit/debit notes, GST register

---

### Phase 12 — Inventory Transactions UI
Manual stock operations, warehouse transfers, adjustments, transaction log, and live balance report.

- `services/inventory.py` — extended with `adjust()`, `list_transactions()`, `get_stock_balance()`
- 6 endpoints under `/api/v1/inventory/`
- Frontend: transactions log, stock balance table, stock-in form, transfer form, adjustment form

---

### Phase 13 — Reports
Read-only analytical reports across all modules with date filters and KPI summary cards.

- `services/reports.py` — 5 pure-SQL aggregation methods: sales summary, purchase summary, production efficiency, GST summary, stock ageing (0-30/31-60/61-90/90+ buckets)
- 5 endpoints under `/api/v1/reports/`
- Frontend: reports hub, sales, purchases, production, GST, stock-ageing pages

---

### Phase 14 — AI Assistant (Full)
Multi-specialist AI agent with live database tool access and Redis conversation history.

- `agents/tools/db_tools.py` — 7 async SQL query functions (stock, transactions, orders, invoices, lots, vendor outstanding, purchase orders)
- `agents/history.py` — Redis conversation history (`erp:chat:{id}`, 24h TTL, 40-message window)
- `agents/specialist/inventory_agent.py` — Anthropic tool_use loop: `get_stock_balance` + `get_recent_transactions`
- `agents/specialist/sales_agent.py` — tool_use loop: `get_sales_orders` + `get_outstanding_invoices`
- `agents/specialist/production_agent.py` — tool_use loop: `get_production_lots`
- `agents/specialist/finance_agent.py` — tool_use loop: `get_customer_outstanding` + `get_vendor_outstanding`
- `agents/specialist/purchase_agent.py` — tool_use loop: `get_purchase_orders` + `get_vendor_outstanding`
- `api/v1/endpoints/agents.py` — intent detection → specialist dispatch → Redis history save
- Frontend: suggested prompt chips, "Querying live data…" indicator, "New conversation" reset button

---

### Phase 15 — Admin Module
Full company administration: user management, role editor, permission assignment, company settings.

- `api/v1/endpoints/admin.py` — 14 endpoints under `/api/v1/admin/`
  - Users: list, invite, update, assign roles
  - Roles: list, create, update (system roles protected), delete
  - Permissions: list all, get/set role permissions
  - Company: get + update settings (GSTIN, PAN, address, operational defaults)
- `schemas/admin.py` — UserOut, CompanyUpdate, RoleCreate, RoleUpdate schemas
- Frontend: admin hub, users table + invite modal, roles list + new role modal, permission editor (grouped by module, indeterminate checkboxes), company settings form

---

### Phase 16 — Notifications & Realtime
WebSocket-delivered real-time alerts + Celery-triggered background notifications.

- `models/notification.py` — Notification model (company_id, user_id nullable, notification_type, title, body, data JSONB, is_read)
- `services/notification.py` — `create_notification()`, `publish_notification()` (sync Redis pub/sub for Celery→FastAPI delivery), `list_notifications()`, `count_unread()`, `mark_read()`, `mark_all_read()`
- `api/v1/endpoints/notifications.py` — 5 REST endpoints + 1 WebSocket:
  - `GET /notifications/count` — unread count
  - `GET /notifications` — list with unread filter
  - `POST /notifications/{id}/read` — mark one read
  - `POST /notifications/read-all` — mark all read
  - `WS /ws/notifications?token=` — JWT-authenticated Redis pub/sub relay
- `workers/tasks.py` — 3 Celery periodic tasks: `check_low_stock`, `check_overdue_payments`, `check_production_delays` — each creates DB notifications then publishes to Redis
- `workers/celery_app.py` — Beat schedules: low-stock daily, overdue-payments daily, production-delays daily
- `components/layout/topbar.tsx` — notification bell: polls count every 30s, WebSocket for real-time, dropdown with type icons + "Mark all read"

---

### Phase 17 — Auth Hardening
Token rotation, account lockout, password reset, and optional TOTP 2FA.

- `core/security.py` — TOTP (pyotp), OTP Redis store (`erp:otp:{email}`, 10 min TTL), rate-limit helper (INCR+EXPIRE), 2FA pending session (`erp:2fa:{session_id}`, 5 min TTL)
- `models/user.py` — added `totp_secret`, `totp_enabled`, `failed_login_count`, `locked_until` + `RefreshToken` model (token_hash stored as SHA-256, expires_at, revoked_at)
- `api/v1/endpoints/auth.py` — full rewrite:
  - `POST /auth/login` — IP rate limit (10/min), lockout after 5 fails (15 min), 2FA gate returns `{requires_2fa, session_id}`
  - `POST /auth/login/verify-2fa` — TOTP verify + full token issue
  - `POST /auth/refresh` — validates token hash in DB, revokes old, issues new (rotation)
  - `POST /auth/logout` — marks refresh token `revoked_at` in DB
  - `POST /auth/change-password` — verifies current password before updating
  - `POST /auth/forgot-password` — rate-limited (5/5 min), OTP stored in Redis; dev mode returns OTP in response
  - `POST /auth/reset-password` — verifies + consumes OTP, updates password
  - `POST /auth/2fa/setup` — generates TOTP secret + `otpauth://` provisioning URI
  - `POST /auth/2fa/enable` — verifies code, sets `totp_enabled=true`
  - `POST /auth/2fa/disable` — verifies password, clears TOTP
- `main.py` — startup DDL: `refresh_tokens` table, totp/lockout columns via `ADD COLUMN IF NOT EXISTS`
- Frontend: login page with inline 2FA step + "Forgot password?" link; `(auth)/forgot-password/page.tsx`; `(auth)/reset-password/page.tsx`; `(app)/settings/security/page.tsx` (change password + 2FA setup with QR code / disable); Sidebar "Security" entry

---

### Phase 18 — Production Readiness
Alembic migrations, S3 storage, Sentry, hardened prod compose, CI/CD pipeline, load testing.

- `db/schema.sql` — updated with `totp_secret`, `totp_enabled` on users table; `notifications` table
- `backend/alembic/versions/001_initial_schema.py` — idempotent baseline migration (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`). Prod startup runs `alembic upgrade head` before uvicorn.
- `backend/app/services/storage.py` — pluggable file storage: `STORAGE_BACKEND=local` writes to `/media`, `STORAGE_BACKEND=s3` uploads via boto3. Provides `upload_file()`, `delete_file()`, `get_presigned_url()`.
- `backend/app/models/master.py` — `FileAttachment` model added
- `backend/app/api/v1/endpoints/attachments.py` — `POST /attachments/upload` (20 MB limit, MIME whitelist), `GET /attachments`, `GET /attachments/{id}/url` (presigned), `DELETE /attachments/{id}`
- Sentry: `sentry-sdk[fastapi]==2.14.0` — auto-initialised in `main.py` when `SENTRY_DSN` is set; `SENTRY_DSN=""` disables it in dev
- `requirements.txt` — added `boto3==1.35.32`, `sentry-sdk[fastapi]==2.14.0`, `locust==2.31.8`
- `docker-compose.prod.yml` — no bind mounts, memory limits on all services, rolling update with `start-first` + automatic rollback, hardened Redis (`maxmemory-policy allkeys-lru`)
- `.github/workflows/ci.yml` — 4-job GitHub Actions pipeline:
  1. `backend-ci` — ruff lint + pytest with real Postgres/Redis service containers
  2. `frontend-ci` — `tsc --noEmit` + eslint
  3. `build-push` — Docker build → GHCR (main branch only), layer cache via GHA
  4. `deploy` — SSH deploy to production server
- `tests/load/locustfile.py` — Locust load test covering auth, products, inventory, sales, purchase, production, finance, notifications, reports, AI chat; weighted by expected traffic
- `.env.example` — complete environment variable template for all 25+ settings

---

---

## Post-Phase-18 Fixes & Features (2026-08-27)

### Auth — Cookie & Token Hardening
- Fixed `secure=True` on refresh token cookie breaking HTTP-only dev (Safari silently drops Secure cookies over HTTP). Changed to `secure=not settings.is_development`, `samesite="lax"`, added explicit `path="/"`.
- Extended axios interceptor to detect stale-permission 403s (`errMsg.startsWith("Permission required:")`) and treat them the same as 401 — call `/auth/refresh` for a fresh JWT then retry.
- JWT access token expiry corrected to **8 hours** (was documented as 15 min; actual config was 8h).
- `(app)/layout.tsx` converted to a client component with a `useEffect` auth guard — redirects to `/login` if no `access_token` in localStorage.
- 71 permissions confirmed seeded in DB and assigned to Administrator role.

### Materials Module (backend)
New raw-material intake workflow built end-to-end.

**Models** (`backend/app/models/inventory.py`):
- `InventoryLot.product_id` made nullable (raw material lots don't require a product link)
- New columns on `InventoryLot`: `bags`, `kg_per_bag`, `trim_type`, `trim_unit`, `split_by_colour`, `split_by_dia`, `notes`
- `MaterialCompositionItem` — fibre name + percentage per lot
- `FabricVariant` — colour / dia per lot
- `TrimVariant` — colour per lot
- `FabricRun` — knitting/weaving run tracking (input_lot_id → output_lot_id, wastage, machine, status)

**Schemas** (`backend/app/schemas/materials.py`): `YarnCreate`, `FabricCreate`, `TrimCreate`, `FabricRunCreate`, `LotOut`, `FabricRunOut`.

**Service** (`backend/app/services/materials.py`): `MaterialsService` with concurrency-safe lot number generation using `SELECT FOR UPDATE` on `document_sequences`. Methods: `create_yarn`, `create_fabric`, `create_trim`, `create_fabric_run`, `list_lots`, `list_fabric_runs`.

**API** (`backend/app/api/v1/endpoints/materials.py`): 7 endpoints under `/api/v1/materials/` — `POST /yarn`, `POST /fabric`, `POST /trims`, `POST /fabric-runs`, `GET /lots`, `GET /lots/{id}`, `GET /fabric-runs`. All protected by `materials.create` / `materials.view` permissions.

### Frontend — Quick Create Workflow
- **Sidebar** — purple `+ Create` button above nav opens `CreateMenu`
- **`CreateMenu.tsx`** — panel with Production (New Lot, New Fabric Run) and Stock (Add Yarn, Add Fabric, Add Trims) sections. Fixed bug where `if (!open) return null` unmounted modal tree before modals could open — panels and modals now render in separate conditional blocks.
- **`ModalShell.tsx`** — shared modal primitives: `Field`, `Input`, `Select`, `Textarea`, `SegControl`, `ModalActions`
- **`NewLotModal.tsx`** — creates production lot via `POST /production/lots`
- **`NewFabricRunModal.tsx`** — creates fabric run, fetches existing lots for input_lot_id
- **`AddYarnModal.tsx`** — ply pills, spinning type, treatment, single/blend composition, Greige/Dyed, bags × kg_per_bag = total weight auto-calc
- **`AddFabricModal.tsx`** — Knit/Woven toggle, 7 knit type pills, GSM/dia, composition, finish multi-select, split checkboxes
- **`AddTrimsModal.tsx`** — 9 trim type pills, 6 unit options, split_by_colour, qty × cost = total value auto-calc

### Frontend — Form/Modal UX
- **Vendor page** (`purchase/vendors/page.tsx`): fixed `onError` reading wrong key (`data.error` vs `data.detail`). Added `parseApiError()` helper. Added auto-code generation from vendor name with ↻ regenerate button.
- **Customer form → right drawer**: `AddCustomerModal` replaced with `AddCustomerDrawer` — slides in from the right at `w-[400px]`, table stays visible.
- **Vendor form → right drawer**: same treatment applied to `AddVendorModal`.

### Inventory — Stock Out Page
- Created `/inventory/stock-out/page.tsx` — "Stock Out — Manual Issue" form calling `POST /inventory/stock-out`
- Fixed inventory hub (`/inventory/page.tsx`) — "Stock Out (Issue)" link was incorrectly pointing to `/inventory/stock-in`; corrected to `/inventory/stock-out`

---

## CRM Module — Phase 1 UI (2026-09-03)

### Modal Overflow Bug Fix
All CRM modal forms were clipping (Save/Cancel buttons hidden) due to two root causes:
1. `(app)/layout.tsx` has `overflow-hidden` on the main wrapper — clips `fixed` children in WebKit/Safari.
2. `flex min-h-full items-center justify-center` causes bidirectional overflow when content exceeds viewport height; `overflow-y-auto` only scrolls downward making the top portion unreachable.

**Fix applied — `frontend/src/components/shared/modal-shell.tsx`:**
- Renders via `createPortal(jsx, document.body)` to escape the CSS containment hierarchy entirely.
- Uses `mx-auto` block centering + `py-8` padding instead of flex centering, so overflow is one-directional and scrollable.
- SSR-safe: `useState(false)` + `useEffect(() => setMounted(true))` guards the portal.
- Escape key closes modal via `window.addEventListener("keydown", handler)`.

### Full-Page "New X" Forms — All CRM Entities
All CRM "New X" creation flows converted from modals to full-page forms matching the existing `crm/customers/new` pattern (sticky header with breadcrumb + Cancel/Save, `max-w-2xl` card sections).

**New pages created:**

| Page | Route | Sections |
|---|---|---|
| New Lead | `/crm/leads/new` | Basic Info (title, pipeline, stage, value, close date, temperature toggle), Contacts & Source (person, org, source, type), Notes |
| New Person | `/crm/persons/new` | Identity (name, job title, city, org), Contact (emails + phone dynamic rows with label selects, WhatsApp) |
| New Organization | `/crm/organizations/new` | Identity (name, website), Address (city, state, country) |
| Log Activity | `/crm/activities/new` | Activity Details (type toggle: call/meeting/note/task/email, title, comment), Link & Schedule (lead, schedule from/to) |
| New Product | `/crm/products/new` | Product Info (name, description, SKU), Pricing & Unit (price, currency, unit) |

**List pages updated (old modal code completely removed):**

| File | Change |
|---|---|
| `crm/leads/page.tsx` | Button → `router.push("/crm/leads/new")`; `NewLeadModal` component, `showModal` state, 4 stale `enabled: showModal` queries all deleted |
| `crm/persons/page.tsx` | Button → `router.push("/crm/persons/new")`; `NewPersonModal`, `ContactRow`, all dead interfaces/constants deleted; file rewritten clean |
| `crm/organizations/page.tsx` | Button → `router.push("/crm/organizations/new")`; `NewOrgModal` deleted; file rewritten clean |
| `crm/activities/page.tsx` | Button → `router.push("/crm/activities/new")`; `LogActivityModal`, stale leads query deleted; file rewritten clean |
| `crm/products/page.tsx` | New-product button → `router.push("/crm/products/new")`; `openCreate` removed; edit modal kept for row-level edits |

**Remaining modals (intentionally kept):**
- `crm/leads/page.tsx` — Import Leads (multi-step CSV upload flow, modal appropriate)
- `crm/products/page.tsx` — Edit Product (inline row edit, modal appropriate)
- `crm/quotes/_components.tsx` — Quote form (complex, not yet converted)
- `crm/leads/[id]/page.tsx` — Convert to SO, Compose Email, Add Activity, Mark as Lost
- `crm/email/page.tsx` — Compose Email
- `crm/whatsapp/page.tsx` — Template Picker
- `crm/settings/page.tsx` — Email Template form, Delete Confirmation

### Cache / Dev Server Notes
- Stale `.next` build cache caused browsers to serve old JS bundles even after source changes.
- **Clear command:** `rm -rf frontend/.next` before restarting the dev server.
- Full restart: `docker compose down && docker compose up --build` (rebuilds backend image too).

---

## Style Master & CRM/Reports Fixes (2026-09-05 → 2026-09-06)

### Style Master — Production Blueprint (Production Module)
Implemented per `docs/Garments_ERP_Style_Master_Specification.md` with strict adherence — the Style Master is now the full production blueprint, not a basic name/code record.

**Backend:**
- Migration `009_style_master.py` — extends `styles` (version, is_active, final_output_unit) and adds 7 child tables: `style_sizes`, `style_colours`, `style_yarns`, `style_fabrics`, `style_processes` (+ `style_sub_processes`), `style_trims`, `style_packing_materials`. Also adds snapshot columns to `production_stages` (tolerance_pct, input_unit, output_unit, conversion_rule, min/max/planned_rate, style_process_id) and `production_lots` (final_output_unit, style_version).
- `models/production.py` — `Style` plus 8 new ORM classes (`StyleSize`, `StyleColour`, `StyleYarn`, `StyleFabric`, `StyleProcess`, `StyleSubProcess`, `StyleTrim`, `StylePackingMaterial`).
- `services/production.py` — `create_style()` persists the full nested blueprint in one transaction; `get_style()` eager-loads all sections. **`create_lot()` rewritten**: when a Style has configured processes, the LOT snapshots those processes (name, tolerance %, units, conversion rule, rate band) onto `ProductionStage` rows instead of the old hard-coded 5-stage sequence (Cutting/Making/Finishing/QC/Packing). Falls back to the generic sequence only when no Style or no configured processes exist. This satisfies the spec's "Style Master → LOT snapshot" and "do not hard-code the workflow" principles — see `docs/PRODUCT.md` §11.1.
- `POST /production/styles` (rewritten), `GET /production/styles/{id}` (new, full detail).

**Frontend:** `/production/styles` (list), `/production/styles/new` (7-section creation form: Basic Info, Sizes/Colours/SKU preview, Yarn, Fabric, Production Workflow with reorderable processes + sub-processes, Trim Planning, Packing Material Planning), `/production/styles/[id]` (detail view).

Verified end-to-end: migration applied, full nested style created via API, LOT created from that style produced exactly its configured processes (not the hardcoded 5) with correct snapshot values confirmed via direct DB query, and the full flow re-verified through a real browser session.

### CRM Activities — Crash Fix, Calendar, Uncheck, Dashboard Popup
- **Fixed a client-side crash** on `/crm/activities`: the frontend expected `activity_type`/`lead_title`/`person_name` fields the backend never returned (only `type` + raw IDs), causing `type.charAt(0)` to throw on `undefined`. Fixed in 3 places: `crm.py` endpoint now joins lead/person/assignee and returns `lead_title`/`person_name`/`assigned_to_name`, plus `activity_type` and `date_from`/`date_to` query filters; `crm/activities/page.tsx` and `crm/activities/new/page.tsx` field names corrected; `crm/leads/[id]/page.tsx`'s "Add Activity" modal had the identical `activity_type`→`type` / `assign_to`→`assigned_to` mismatch (silently broke activity creation from the lead detail page) plus a free-text assignee input replaced with a proper user picker.
- **Added a Teams-style calendar view**: List/Calendar toggle on the Activities page. Month grid (Mon–Sun) with activities plotted on their scheduled date as colour-coded chips by type, today highlighted, prev/next/Today navigation, and a day-detail slide-over panel.
- **Uncheck support**: `PATCH /crm/activities/{id}/done` now accepts `{is_done: bool}` (defaults `true`); the checkmark toggles both ways everywhere (list, calendar panel, lead-detail feed) instead of being one-directional.
- **Dashboard "Today's Activities" popup** on `/dashboard`: bottom-right card showing today's scheduled activities, dismissible per-day (sessionStorage), links to the full Activities page. Hidden entirely when nothing is scheduled.

**Two subtle pre-existing bugs surfaced and fixed while building the popup:**
1. `/dashboard` is statically prerendered at build time but rendered `new Date()` directly in JSX — the header's date/greeting was frozen at build time and mismatched the client on every load (React hydration error). Fixed by computing it only after mount (`useState`+`useEffect`), not by suppressing the warning (which would have frozen the header forever at the wrong value).
2. **App-wide CSS bug**: `globals.css` has `main > * { animation: fade-in 0.28s ease both; }` for the page-entrance effect. Because of `animation-fill-mode: both`, every page's root div permanently retains `transform: translateY(0)` (an identity transform) after the animation ends — and per the CSS spec, *any* non-`none` transform on an ancestor creates a new containing block for `position: fixed` descendants. This silently breaks corner-anchored (`bottom-*`/`right-*`) fixed elements rendered inline in page JSX, positioning them relative to the scrollable page content instead of the viewport. Fixed by rendering the dashboard popup and the Activities calendar's day-detail panel through the existing `ModalPortal` component (portals to `document.body`), the same pattern already used for other overlays in the codebase — rather than touching the shared global animation rule.

### Inventory — Material Lots Trim-Type Filter
Added a second-level filter row on `/inventory/lots` when the "Trims" tab is active: pills built dynamically from the real distinct `trim_type` values in the data (with counts), not a hardcoded category list — since actual trim records use specific names ("Button 12L", "Drawcord 6mm") rather than coarse categories. Backend: new `GET /materials/lots/trim-types` endpoint + `trim_type` filter param on `GET /materials/lots`.

### Reports — Stock Ageing Fix, Dummy Data, Charts
- **Fixed a real backend bug**: the stock-ageing SQL selected `u.symbol`, but the `units` table's column is `abbreviation` — every request 500'd silently (the frontend swallows query errors and shows an empty table), so the report always appeared empty regardless of actual stock.
- Added a `stock_value` column to the query (quantity × weighted-average receipt cost) so ageing can be judged by value, not just SKU count.
- Inserted realistic dummy inventory receipts (fabric/yarn/trims/finished goods, multiple warehouses) backdated across all four buckets — this also surfaced pre-existing real stock that had been invisible the whole time due to the bug.
- Added a bar chart (stock value by ageing bucket) and a donut chart (% value share by bucket) to `/reports/stock-ageing`, plus a value figure on each bucket's stat card.

### Dev Environment
- `docker-compose.yml` backend command now passes `--timeout-graceful-shutdown 5` to uvicorn's `--reload` — the dev server repeatedly hung on "Waiting for background tasks to complete" during hot-reload (an open WebSocket connection from a browser session blocking shutdown), requiring manual container restarts. Bounding the graceful-shutdown window fixes this.

---

## CRM Enhancement — Lead Lifecycle, Analytics, Pricing & WhatsApp Automation (2026-10-02)

Full implementation of Phases 1–8 of `docs/CRM upgrade after 07092026 call.md` (of 18 total) — lead assignment and follow-up lifecycle, employee task system, platform-wise lead analytics, ad spend/acquisition cost, catalogue pricing tied to the real ERP product master, and configurable WhatsApp automation. All additive — no destructive migrations, no behavior change to any already-shipped CRM page.

### Phase 1 — Lead Assignment to Employees
- `CrmLead` gained `assigned_date`/`assigned_by`/`assignment_status`; new `CrmLeadAssignmentHistory` audit table.
- New `POST /crm/leads/{id}/assign` via a shared `_assign_lead()` helper (reused by bulk-assign).
- New `crm.assign` permission, auto-granted to any role already holding `crm.edit`.
- New `GET /crm/assignable-users`, deliberately gated on `crm.view` (not `admin.users`) — fixes a real permission mismatch that would have blocked ordinary sales users from seeing who leads could be assigned to.
- Frontend: "My Leads" filter + an Assignment card on the lead detail page.
- Migration `020_crm_lead_assignment.py`.

### Phase 2 — Lead Follow-Up Management
- `CrmLead` gained `next_follow_up_at`/`follow_up_type`/`follow_up_reason`/`follow_up_notes`/`follow_up_status`/`last_contacted_at`/`contact_outcome`/`next_action`.
- New `CrmFollowUpType` lookup table, seeded with 12 types.
- New `_sync_lead_followup_fields()` — recomputes the lead's forward-looking follow-up fields from the nearest undone activity; runs after every activity create/update/delete/done-toggle.
- `ActivityDoneUpdate` extended so completing an activity can schedule the next follow-up in the same call.
- New `CompleteActivityModal` on the frontend.
- **Bug found and fixed:** this project's DB sessions run with `autoflush=False`; `_sync_lead_followup_fields()`'s internal SELECTs were reading stale pre-commit data. Fixed with explicit `await db.flush()` before the recompute in `update_activity`/`mark_activity_done` — caught via a failing curl test, not by code review.
- Migration `021_crm_followups.py`.

### Phase 3 — Employee Task System
- New `CrmTask` model (title, notes, lead/customer link, assignee, due date, priority, status, source) + full CRUD + `/complete` endpoint.
- Auto-task creation wired into `_assign_lead()` ("Make first contact").
- New Celery beat task `flag_missed_followups` (idempotent — skips leads that already have an open missed-follow-up task).
- New `/crm/tasks` page, dashboard "My Tasks" section, "Employee Task Performance" report.
- **Bug found and fixed (the one that changed this effort's whole verification process):** Next.js App Router forbids a `page.tsx` from exporting anything besides the page component — `export { CreateTaskModal }` from `crm/tasks/page.tsx` passed `tsc --noEmit` cleanly but failed a full `next build`. Fixed by moving the modal to `frontend/src/components/crm/create-task-modal.tsx`. A full `next build` (not just `tsc --noEmit`) became mandatory before every Docker rebuild from this point on.
- Migration `022_crm_tasks.py`.

### Phase 4 — Platform-Wise Lead Analytics
- `CrmLeadSource` existed but was read-only (no create/update/delete endpoint — one platform, "IndiaMart", had been inserted directly via SQL). Added full CRUD mirroring the existing `Category` pattern in `master.py`, plus a unique `(company_id, name)` constraint and an in-use guard on delete.
- New `platform_lead_analytics` report (`qualified` defined as `temperature IN ('warm','hot')` — stated as an explicit interpretive judgment call, not a spec-given definition).
- New `/crm/settings` "Lead Sources / Platforms" management section.
- Migration `023_crm_lead_sources_crud.py` seeds the spec's missing platforms (WhatsApp, Instagram, Facebook, Google, Direct) without duplicating the existing IndiaMart row.

### Phase 5 — Lead Acquisition Cost
- New `CrmAdSpend` ledger (source, campaign, period, amount, notes).
- New `lead_acquisition_cost` report: `cost_per_lead`/`cost_per_qualified_lead`/`cost_per_conversion`/`roas`, each computed via SQL `CASE WHEN` so a zero or missing denominator yields `NULL` — never a fabricated `0`.
- Verified exact arithmetic: ₹6,000 logged against a platform's known 5 leads → `cost_per_lead = 1200.00` exactly.
- New `/crm/ad-spend` ledger page under a new "Marketing" nav group.
- Migration `024_crm_ad_spend.py`.

### Phase 6 — Ad Spend Management
- Extended `CrmAdSpend` with `campaign_id`, `ad_set`, `impressions`, `clicks`, `source` (defaults `"manual"` — architecturally ready for a future ad-platform API sync, but no such integration exists; nothing invented against the "no credentials" rule).
- New `POST /crm/ad-spend/import` CSV endpoint (mirrors the existing lead-CSV importer); unrecognized platform names auto-create a new `CrmLeadSource` row.
- `/crm/ad-spend` became a real dashboard: date-range KPI tiles, spend-by-platform and spend-by-campaign breakdowns (campaign breakdown is spend-only — campaigns aren't attributable to individual leads, so no fabricated cost-per-lead-by-campaign).
- Migration `025_crm_ad_spend_fields.py`.

### Phase 7 — Catalogue & Activity-Based Pricing
The biggest architectural call of this effort. `CrmQuoteItem.product_id` pointed at a separate, disconnected `CrmProduct` table instead of the real ERP `Product`/`ProductVariant` master — directly contradicting the spec's own "do not duplicate product master data" instruction, but pre-existing and carrying live quote data with no reliable remap path. **Resolved additively, not by rip-and-replace:**
- All new pricing work (`PriceList`/`PriceListItem`, already modeled but completely unwired — zero endpoints, zero UI, and `PricingService.get_price()` only ever read `Product.mrp`) is built exclusively against the real ERP product master.
- `CrmQuoteItem` gained new, nullable `erp_product_id`/`erp_variant_id` columns alongside the untouched legacy `product_id`; the CRM quote item picker now offers both paths side by side.
- `PriceListItem` extended with `customer_id` (true per-customer override) and `valid_from`/`valid_to`; new `PriceHistory` table logs every price change.
- `PricingService.get_price()` rewritten with a 3-tier resolution order (customer override → generic list price → `Product.mrp` fallback → not found), each tagged with a `source` field.
- New `CrmLeadProduct` join table (structured lead→product interest), replacing the free-text-only "Catalogue Sent" label.
- New `/sales/price-lists` page; "Interested Products" card on the lead detail page.
- Verified: a customer override price correctly beat the generic list price, which correctly beat the MRP fallback; a quote mixing an ERP-priced item, a legacy `CrmProduct` item, and a plain custom line item all coexisted correctly.
- Migration `026_crm_pricing.py`.

### Phase 8 — WhatsApp Integration & Automated Communication
- WhatsApp sends are fully configurable — no message is hard-coded into business logic. New `WhatsappAutomationRule` (trigger event, template-or-freeform-body, recipient type, delay, enable/disable) and `WhatsappAutomationLog` (per-send audit trail) tables.
- New `template_render.py` (`{{var}}` substitution) and `whatsapp_automation.py` (`fire_event()` dispatcher + phone-resolution fallback chain: `CrmPerson.whatsapp_number` → `contact_numbers[0]` → `Customer.whatsapp_no` → `Customer.mobile` for customers, `User.phone` for employees).
- Sends are always routed through a new Celery task (`send_whatsapp_automation`), never inline — the existing Meta Graph API integration (`backend/app/api/v1/endpoints/whatsapp.py`) is real but has no credentials configured, so a slow/failing external call can never block the CRM action that triggered it.
- Wired into 5 trigger points: `_assign_lead` (lead assigned), `add_lead_product` (catalogue shared, reusing Phase 7's structured link), `create_quote` (quotation generated), `flag_missed_followups` (follow-up due — fires only once overdue, since no proactive "about to become due" scheduler exists), and a new check in `create_activity` for the `"Sample Sent"` activity type (sample dispatched).
- New `/crm/whatsapp-automation` page (rules + send log) — the existing 776-line WhatsApp inbox page was left untouched.
- **Two bugs found and fixed:**
  1. `WhatsappAutomationRule`/`Log` had no Python-side default for `created_at`/`updated_at`; SQLAlchemy sent an explicit `NULL` on insert instead of deferring to the DB's `server_default NOW()` — every create 500'd. Reproduced the same failure on the pre-existing (never-exercised) `WhatsappTemplate` create endpoint, confirming it wasn't new. Fixed with Python-side `default=`/`onupdate=` on the two new models.
  2. The Celery `_run()` helper's new-event-loop-per-task pattern was leaking pooled asyncpg connections across loops, intermittently crashing **every** scheduled task in the app with "attached to a different loop" (reproduced live in `celery_worker` logs). Fixed by disposing the shared engine's pool at the end of `_run()`.
- Verified live: all 5 triggers fire with correct recipient resolution and variable substitution, correctly fail with the genuine Meta "no credentials" error (not a code bug), correctly skip with `skipped_no_phone` when no phone resolves, and produce zero sends when a rule is disabled.
- Migration `027_whatsapp_automation.py`.

### Known limitations (stated, not silently papered over)
- No real WhatsApp Business API credentials are configured (`WHATSAPP_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID`) — automation sends will log `status="failed"` with a genuine Meta API error until a human supplies them.
- `CrmProduct`/`CrmQuoteItem.product_id` (pre-existing, Phase 7) remains as a legacy path alongside the new ERP-backed pricing — not removed, since live quote data points at it with no reliable remap.
- Follow-up-due automation only fires once a follow-up is already overdue, not proactively ("about to become due").
- Sample-dispatched automation keys off the free-text `"Sample Sent"` activity type rather than a new structured entity.

---

## How to Run (Dev)

```bash
# 1. Start Docker services
docker-compose up -d postgres redis

# 2. (First time only) Seed database
cd backend && .venv/bin/python -m app.db.seed

# 3. Backend  (from backend/)
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend  (from frontend/, new terminal)
npm run dev
```

Open **http://localhost:3000** — login with `admin@company.com` / `Admin@1234`

Swagger docs: **http://localhost:8000/api/v1/docs**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 (Docker) |
| Migrations | Alembic 1.13 (async) |
| Cache / Queue | Redis 7 |
| Backend | FastAPI 0.115, SQLAlchemy 2.x async, asyncpg |
| Auth | JWT (python-jose), bcrypt 4.x, pyotp 2.9 (TOTP), httpOnly refresh cookie |
| Task queue | Celery 5.4 + Redis broker |
| AI | Anthropic tool_use loop, Claude Sonnet 5, Redis conversation history |
| Storage | Local FS (dev) / AWS S3 via boto3 (prod) |
| Observability | structlog (structured JSON logging), Sentry SDK |
| Frontend | Next.js 14.2, Tailwind CSS, TanStack Query v5, React Hook Form, Zod, axios |
| Proxy | nginx |
| Containers | Docker + docker-compose |
| CI/CD | GitHub Actions → GHCR → SSH deploy |
| Tests | pytest-asyncio, pytest-cov, Locust (load) |
