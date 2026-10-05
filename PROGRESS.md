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

Full implementation of Phases 1–8 of `docs/CRM upgrade after 07092026 call.md` (of 15 total) — lead assignment and follow-up lifecycle, employee task system, platform-wise lead analytics, ad spend/acquisition cost, catalogue pricing tied to the real ERP product master, and configurable WhatsApp automation. All additive — no destructive migrations, no behavior change to any already-shipped CRM page.

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

## ERP Upgrade — Sales/Inventory Add-ons (2026-10-02 →)

Separate, unphased requirements doc (`docs/ERP upgrade after 07092026 call.md`
— Sales Order / Inventory / Stock Management), distinct from the CRM
enhancement doc above. Research split its 16 sections into EXISTS/PARTIAL/GAP
and proposed an 8-phase build order (wholesale pricing → SO inventory
check/reservation → Packing Slip → SO-against-PO tolerance → stock balance
filtering → stock adjustment/transfer hardening → product merge → stock
value admin-only + transaction log attribution). Incidental find during
research: the `refresh_inventory_balance` Celery beat task targets a
materialized view that **no migration ever created** — orphaned, silently
erroring every run; not yet fixed (out of scope for Phase 1, flagged here).

### Phase 1 — Default Wholesale Pricing
- `Product`/`ProductVariant` gained a nullable `wholesale_price` column
  (`backend/app/models/master.py`), additive alongside the existing
  `mrp`/`dealer_price`/`cost_price`.
- `PricingService.get_price()` (`backend/app/services/pricing.py`) — the
  fallback tier (previously `Product.mrp` only) now checks
  `wholesale_price` first (`source="wholesale"`), falling back to `mrp`
  (`source="mrp"`) only when wholesale isn't set — backward-compatible for
  every existing product, tier order above it (customer price-list →
  generic price-list) unchanged.
- Real finding: `backend/app/services/sales.py` never called
  `PricingService` at all — Sales Order/Quotation `unit_price` was raw
  client input defaulting to `"0"` in the frontend forms, with zero
  auto-population anywhere in the actual ERP sales flow (only the CRM
  quote picker, a CRM Phase 7 addition, had price suggestion wired in).
  Wired `/sales/orders` and `/sales/quotations` product pickers to call
  the existing `GET /sales/price-lists/resolve` endpoint and suggest
  `unit_price` (shown as "Suggested from {source}", editable, never
  overwrites a price the user already changed) — same UX already shipped
  in the CRM quote picker.
- `wholesale_price` added to the Product master Add/Edit forms
  (`frontend/src/app/(app)/inventory/products/page.tsx`), same pattern as
  the existing `mrp`/`dealer_price`/`cost_price` fields.
- Migration `028_wholesale_price.py`.
- Verified: wholesale (₹180) correctly beat MRP (₹220) with no price-list
  match; MRP fallback confirmed for a product with no wholesale price set;
  customer-specific list price (₹450) still correctly beat generic list
  price (₹550), which still correctly beat wholesale (₹180) — full 4-tier
  order intact. Regression-checked CRM quotes and the Phase 7 price-lists
  page — unaffected (shared `PricingService` code path).

### Phase 2 — Sales Order Inventory Check & Reservation
- No new column needed — `SalesOrderItem.delivered_qty` (already
  maintained correctly by `create_delivery`) plus `SalesOrder.status` were
  composed into a live "committed quantity" aggregate instead of building
  a separate reservation ledger: `SUM(GREATEST(quantity - delivered_qty,
  0))` across all `sales_order_items` whose parent order isn't cancelled.
- New `InventoryService.get_total_balance()` (physical balance across all
  warehouses — Sales Orders don't carry a `warehouse_id`, that's only
  chosen at Delivery time) and `SalesService.get_committed_quantity()`
  (`backend/app/services/inventory.py`, `backend/app/services/sales.py`).
- New `GET /sales/orders/stock-check` endpoint returning Ordered/
  Available/Committed/Remaining + a `can_fulfill` flag.
- **Explicitly informational, not blocking** — the spec says the user
  should be able to "identify" fulfillability, never says to reject an
  order; apparel manufacturers routinely take orders against future
  production. Verified directly: an order for 99,999 units against ~1,900
  available still creates successfully, with `can_fulfill=false` surfaced
  for the user to see, not enforced.
- Frontend: `/sales/orders`' line-item product picker now shows "{avail}
  avail · {committed} committed · {remaining} remaining" (amber when the
  ordered qty exceeds remaining), re-checked on product change and on
  quantity blur. `/sales/quotations` deliberately untouched — a quotation
  is pre-commitment, so no stock check belongs there.
- Verified: 2 open SOs (30 + 20 units) → committed correctly summed to 50;
  delivering 10 of the first dropped committed to 40 (proving the
  `delivered_qty`-aware aggregate, not a naive `SUM(quantity)`); cancelling
  the second dropped it to 20 (cancelled orders correctly excluded).

### Phase 3 — Packing Slip
- Reused the existing `Delivery`/`DeliveryItem` model as the Packing Slip
  rather than building a parallel entity — it was already SO-linked,
  customer-linked, and drove real stock-out; it just had no packing-
  specific fields. Added `carton_count`, `package_count`, `packing_marks`,
  `gross_weight`, `net_weight` (additive, header-level, same tier as the
  existing `transporter`/`lr_number`/`vehicle_number` dispatch fields) —
  migration `029_packing_slip_fields.py`.
- The existing "Delivery Challan" label/page is deliberately left
  unrenamed — in Indian business practice it's a distinct GST-adjacent
  transport document; the Packing Slip is generated **from** a Delivery
  record as a new printable view, not a rename of the existing one.
- This is the **first printable sales document** in the app (confirmed
  via research — zero existing pdf/print code anywhere in `sales.py`,
  backend or frontend). New `backend/app/services/packing_slip.py` +
  `backend/app/templates/packing_slip.html` (Jinja2 + WeasyPrint, same
  brand styling as the Reports Hub's PDF export, but its own document
  layout — company header, SO reference, customer block incl. GSTIN/
  address, items table, packing + dispatch sections — since
  `report_export.py`'s renderer is explicitly generic/tabular only).
- New `GET /sales/deliveries/{id}/packing-slip` → real PDF, generated
  entirely server-side from the existing Delivery record (no new data
  from the caller). Frontend: a print icon on each delivery row
  downloads it via the same blob pattern already used by the Reports Hub
  PDF export (`frontend/src/components/reports/report-page.tsx`); the
  create-delivery modal gained a "Packing Details" section.
- Verified: PDF confirmed valid (`%PDF-1.7` magic bytes) and, via
  `pdftotext`, confirmed to contain the real SO number, customer name,
  product, and quantity — not placeholders; a delivery created with no
  packing fields at all renders cleanly with "—" throughout, no crash on
  nulls.

### Phase 4 — Sales Order Against Purchase Order (±5% Tolerance)
- New `SalesOrder.customer_po_number`/`customer_po_quantity`/
  `po_tolerance_pct` (all nullable, header-level) — migration
  `030_so_po_reference.py`.
- Enforcement follows this codebase's existing "rule logic lives in
  `BusinessRulesEngine`, not hard-coded into the calling service" pattern
  exactly: new `validate_po_quantity()` in `backend/app/domain/
  business_rules.py`, mirroring the existing `validate_material_issue()`'s
  shape (a caller-supplied `tolerance_pct_allowed`, not a constant baked
  into the rule — and that value itself is sourced the same way
  `StyleProcess.tolerance_pct` already works: a real per-record column,
  not a global setting). `create_sales_order` raises `BusinessRulesError`
  before creating any row when a referenced PO's quantity is breached;
  the endpoint converts it to a 422, identical to the existing
  `inventory.py` pattern for the same exception type.
- **Deliberately enforced, not just informational** — the explicit
  contrast with Phase 2's stock check: §2 said the user should "identify"
  fulfillability (informational), §5 says the system "should validate"
  (directive) — this phase actually rejects out-of-tolerance orders.
- Only runs when a PO quantity is actually given; a Sales Order not
  referencing a PO is never checked.
- **Found and fixed a real pre-existing bug while here**: this app's
  error envelope for business-rule/HTTPException errors is `{"error":
  ...}` (see `backend/app/main.py`'s exception handlers), not FastAPI's
  default `{"detail": ...}` — but `/sales/orders`' create-modal `onError`
  was reading `.detail` only, silently swallowing every business-rule
  error (including this phase's own new tolerance message) behind a
  generic "Failed to create sales order" fallback. Fixed by reusing the
  `parseApiError()` helper already proven in `purchase/vendors/page.tsx`
  (handles both envelope shapes). Not fixed elsewhere — same latent gap
  likely exists in other modals copy-pasting the old `.detail`-only
  pattern, flagged here rather than silently expanded into a wider sweep.
- Verified live: PO qty 1000 + order qty 980 → 201 (within ±5%); PO qty
  1000 + order qty 800 → 422 with the exact allowed range in the message;
  no PO quantity at all → always succeeds; PO qty 1000 + `po_tolerance_pct
  =10` + order qty 920 (outside ±5%, inside ±10%) → 201, proving the
  tolerance is genuinely per-order configurable, not hard-coded to 5.

### Phase 5 — Stock Balance Filtering
- `GET /inventory/balance` took zero query params before this phase —
  confirmed via direct code read, not assumed. `InventoryService.
  get_stock_balance()` extended (not rebuilt) with `product_id`,
  `category_id`, `warehouse_id`, `customer_id`, `status` filters, plus a
  `LEFT JOIN product_variants`/`categories` for `sku`/`category_name` that
  didn't exist in the row shape at all before.
- **A real fix, not just a new param**: the old query hard-coded `HAVING
  SUM(...) != 0`, silently hiding every zero/negative (oversold) balance
  with no way to see them. Replaced with an explicit `status` param
  (`in_stock` / `out_of_stock` / `all`); backend default is now `all`
  (an API shouldn't hide data unless asked), while the frontend's own
  default tab is "In Stock" so the everyday view looks the same as
  before. This immediately surfaced a real oversold variant that the old
  query's implicit per-product netting had been masking — confirmed
  live, not hypothetical.
- `customer_id` filter is deliberately narrow: restricts rows to products
  appearing in that customer's own non-cancelled Sales Orders (an
  `EXISTS` check), not a new computed "committed to this customer"
  metric — the spec's own "Customer/order context where applicable"
  wording was read literally rather than expanded into something it
  didn't ask for.
- SKU got no separate picker — once `sku` is in the row data, the
  existing free-text search box was extended to also match it, avoiding
  a redundant control for the same "find this item" interaction.
- Frontend: 4 new filter dropdowns (Product/Category/Warehouse/Customer,
  reusing the already-existing `filter-sources.ts` hooks — zero new
  data-fetching code) + a 3-way status tab strip, both wired to real
  server-side query params for the first time.
- **Known limitation, stated explicitly**: a product that has *never* had
  any inventory transaction still won't appear even under `status=all`,
  since the query is still driven from the transaction ledger, not the
  product master — extending the existing query rather than rebuilding
  it product-first.
- Verified live: default (no params) now returns rows the old hard-coded
  query would have hidden; `in_stock`/`out_of_stock` partition correctly;
  `category_id` and `warehouse_id` filters return only matching rows;
  `customer_id` correctly scopes to that customer's own orders and
  returns an empty list (not an error) for a customer with none.

### Phase 6 — Stock Adjustment Unification + Transfer Hardening
- `POST /inventory/adjust` previously only supported "Replace" (an
  absolute `new_quantity`, delta computed server-side) — confirmed via
  direct code read, not assumed. Unified into one workflow: `AdjustRequest`
  now takes `adjustment_type: "add"|"reduce"|"replace"` + `quantity`
  (meaning depends on type). Single existing caller (the Adjust page), so
  the request shape was changed cleanly rather than kept dual-shaped.
- **Found and fixed a real pre-existing gap while reading this code**:
  `BusinessRulesEngine.validate_stock_adjustment()` (checks the resulting
  balance isn't negative) existed but was **never called anywhere** —
  `adjust()` had no negative-balance guard at all, unlike `issue()`/
  `transfer()` which both correctly call their sibling rules. Now wired
  in for all three modes; verified live that a `reduce` large enough to
  go negative is correctly rejected with 422.
- `InventoryTransaction` gained `previous_balance`/`new_balance`/
  `adjustment_type` (populated only for adjustment rows — the spec's
  "Existing/Resulting quantity" ask is explicitly under §8, not
  retrofitted onto `receive`/`issue`/`transfer`) and `transfer_group_id`
  (a shared UUID stamped on both the `transfer_out`/`transfer_in` rows of
  one transfer, so the two sides "remain traceable" per §9 via a hard
  value instead of matching quantity/date/notes after the fact).
- Frontend: the Adjust page redesigned around a 3-way Add/Reduce/Replace
  tab strip (one workflow, not three screens); shows the current balance
  live (reusing Phase 5's filterable `/inventory/balance`) and a computed
  resulting-balance preview before submit. Fixed the same `.detail`-only
  error-reading bug found and fixed on the Sales Order page in Phase 4.
- Verified live: `add`/`reduce`/`replace` all produce the exact expected
  `previous_balance`/`new_balance` pair; a transfer's two rows share one
  `transfer_group_id`, confirmed independently via the Transaction Log
  endpoint, not just the immediate response.

### Phase 7 — Product Merge
- Complete gap before this phase — zero product-merge code anywhere.
  Before writing any code, swept the **entire** backend for every table
  referencing `products.id` (14 tables, 11 with required/NOT NULL FKs) —
  missing even one would have left orphaned data after a merge. Full list
  recorded in the plan file for future reference.
- `MergeService.merge_products()` (`backend/app/services/
  product_merge.py`) reparents the source product's own `ProductVariant`
  rows to the target, then repoints all 13 other tables' `product_id` (or
  `erp_product_id`) from source → target, in one atomic transaction
  (single commit at the end) — directly satisfies "prevent accidental
  duplicate stock creation during the merge."
- **Consolidating stock needed no separate write**: since
  `inventory_transactions.product_id` is one of the repointed columns,
  and Stock Balance (Phase 5) sums the ledger live, the target's balance
  is automatically correct the moment the ledger rows move — verified
  live, not assumed.
- Source product is deactivated (`is_active=false`, the already-existing
  but previously-unused `deleted_at` finally wired to something real),
  never deleted, and gets a new `merged_into_id` pointer so "previous
  product references remain traceable."
- New narrow `product_merge_logs` table for this phase's own audit trail
  — **deliberately not** `docs/PRODUCT.md`'s larger generic `audit_logs`
  design (which spans every entity type in the app and was never
  implemented) — scoped literally to what §10 asks for, not expanded into
  that separate, much bigger, unrequested effort.
- New `master_data.merge` permission (auto-granted to roles already
  holding `master_data.delete`), guarding a new `POST /products/{id}/merge`
  + `GET /products/merge-logs`.
- One merge rule handles both "can't re-merge" and "can't reverse-merge
  into something already merged away": reject if the source is already
  merged, or if the target isn't currently active.
- Frontend: a Merge action on each product row (confirmation modal with
  an explicit "cannot be easily undone" warning), a "Merged → {target}"
  status badge replacing the plain "Inactive" label, and a collapsible
  Merge History panel.
- Verified live end-to-end: logged a sales order item, a quotation item,
  and a +30 stock adjustment against a throwaway product, merged it into
  a second throwaway product, and confirmed all three references now
  point at the target and the target's stock balance is exactly 30 —
  not approximated, not double-counted. Re-merging the same (now-merged)
  source, and merging into the now-inactive source, both correctly
  rejected with clear 400s. Test products and their data cleaned up
  afterward.

### Phase 8 (final) — Stock Value Admin-Only Visibility + Transaction Log Attribution
- No `has_permission()` boolean check existed anywhere in this app before
  this phase — `CurrentUser` (`backend/app/api/v1/deps.py`) only had
  `require()` (a hard 403). Added `has_permission()` alongside it, used
  **only** for field-level redaction, never to replace `require()`'s
  endpoint-level block. This is the first precedent in the codebase for
  an endpoint conditionally nulling a response field by permission rather
  than hiding it in the UI — confirmed via research that nothing like it
  existed before writing it.
- New `inventory.value` permission, granted directly to the role named
  `Administrator` via migration (seed.py's `PERMISSIONS` list was also
  updated, but only matters for a fresh install — seeding is one-time and
  doesn't retroactively apply to this already-running database, so the
  migration is what actually makes it real here).
- `StockBalanceRow` gained `stock_value` (it had no value field at all
  before — `SUM(quantity * direction * unit_cost)`, the same weighted-
  cost convention the pre-existing Stock Ageing report already uses, not
  a new costing method). `TransactionOut.unit_cost`/`total_cost` are now
  nulled for any caller without `inventory.value`, enforced in the
  endpoint before the response is built — **verified literally in the
  JSON response**, not just hidden in the frontend: a real non-admin test
  user (same login flow) received `stock_value: null` and `unit_cost:
  null`/`total_cost: null` while `balance`/`product_name`/quantity stayed
  fully visible, matching §11's quantity-visible/value-admin-only split
  exactly.
- **Found and fixed a real display bug while here**: the Transaction Log
  page was rendering raw `product_id`/`warehouse_id` UUIDs as text (not
  names), and would have shown `₹NaN` for any null cost field once this
  phase introduced one. `list_transactions()` now joins `products`,
  `product_variants`, `warehouses`, and `users` to resolve real names,
  and both the balance and transaction pages render `"—"` for a withheld
  value instead of `₹0.00`/`₹NaN` — never misreporting "no access" as
  "zero."
- §12's "immutable... rather than allowing users to silently rewrite" was
  already satisfied going in — confirmed via grep that no PATCH/DELETE
  endpoint for transactions exists anywhere; nothing needed building.
- Verified live: hand-computed stock value for a real multi-warehouse
  product (40 units @ ₹10 + 150 units @ ₹165 = ₹25,150) matched the
  endpoint's `stock_value` sum exactly, split correctly across its two
  warehouse rows (₹400 + ₹24,750).

---

## ERP Upgrade — 8-Phase Rollup (2026-10-02)

All 8 phases of the proposed breakdown of `docs/ERP upgrade after
07092026 call.md` are complete and verified end-to-end against the live
Docker stack: **Phase 1** Default Wholesale Pricing, **Phase 2** Sales
Order Inventory Check & Reservation, **Phase 3** Packing Slip, **Phase 4**
Sales Order Against Purchase Order (±5% Tolerance), **Phase 5** Stock
Balance Filtering, **Phase 6** Stock Adjustment Unification + Transfer
Hardening, **Phase 7** Product Merge, **Phase 8** Stock Value Admin-Only
Visibility + Transaction Log Attribution.

**Real pre-existing bugs found and fixed along the way** (not introduced
by this effort, surfaced by it): the Sales Order/Quotation forms never
called the pricing service at all (Phase 1); `validate_stock_adjustment()`
existed but was never wired in, leaving adjustments with no negative-
balance guard (Phase 6); the Sales Order and Stock Adjustment pages' error
handling read the wrong JSON field (`.detail` instead of this app's real
`.error`), silently swallowing every business-rule message (Phases 4, 6);
the Transaction Log page rendered raw UUIDs instead of names (Phase 8).

**Known limitations, carried forward deliberately, not silently dropped**:
- SO inventory/PO-tolerance checks are company-wide totals, not per-
  warehouse (Sales Order items don't carry a warehouse — only Delivery
  does, which already does the correct per-warehouse check at dispatch).
- Stock Balance still can't show a product that has *never* had any
  ledger transaction, even under `status=all` — it's driven from the
  transaction ledger, not the product master.
- The pre-existing `CrmProduct`/`CrmQuoteItem.product_id` duplicate-master
  path (from the CRM upgrade effort) still coexists alongside the real
  ERP product master — untouched, since fixing it was never in scope here.
- Product Merge's audit trail (`product_merge_logs`) is narrow and
  merge-specific — not `docs/PRODUCT.md`'s larger generic `audit_logs`
  design, which remains unimplemented and out of scope for this effort.

---

## Production Module — End-to-End Test + Dummy Data Backfill (2026-10-02)

Two full production lifecycles run live against the real API (Style →
Lot → Stages → Entries → Job-Work Challans → Material Issue → Output →
Additional Costs → Fabric Processing → status progression → PDF report),
deliberately varied between the two runs (yarn-sourced vs purchased-fabric
style, vendor-assigned vs worker-assigned job work, straight-through
completion vs cancel-then-reopen) to flush out path-dependent bugs.

**2 real bugs found and fixed:**
1. A job-work challan with **neither** `vendor_id` nor `worker_id` was
   wrongly accepted (should always require exactly one). Root cause:
   Pydantic v2's `@field_validator` silently skips a field left at its
   default (unprovided) value unless `validate_default=True` is set — so
   the existing validator only ever caught the "both provided" case, not
   "neither." Fixed by switching to a `@model_validator(mode="after")` on
   `StageChallanCreate` (`backend/app/schemas/production.py`), which
   always runs regardless of which fields were supplied. Confirmed this
   exact pattern (`bool(x) == bool(y)` in a single-field validator) didn't
   recur anywhere else in the schemas.
2. `TransactionOut.product_name`/`warehouse_name`/`created_by_name` (added
   in the ERP Upgrade's Phase 8) came back `null` from the 4 single-
   transaction creation endpoints (stock-in, stock-out, transfer, adjust)
   — only the `list_transactions` endpoint ever resolved them. Fixed with
   a shared `_enrich()` helper in `backend/app/api/v1/endpoints/
   inventory.py`, applied to all 4 creation endpoints.

**Known gaps found, disclosed rather than silently built or ignored:**
- `ProductionLotSize.cut_qty`/`sewn_qty`/`finished_qty` are written once
  at lot creation and never updated anywhere in the lifecycle — stage
  entries track aggregate pieces, not a per-size breakdown, so these
  three fields are structurally dead. Confirmed via grep: zero write
  sites beyond initial creation. Not fixed — allocating stage-level
  entries across sizes without a size_id on the entry itself is a real
  design decision, not a bug fix, and was left for the user to prioritize.
- No delete/cancel endpoint exists for a job-work challan — a mistaken
  challan can only be removed via direct DB access, not the API.
- `ProductionStage.assignment_type` locks in on the *first* challan's
  type and never updates again for that stage — confirmed intentional
  (one stage, one assignee for its lifecycle), not a bug.

**Dummy data backfill** (scoped to the Production module, per "for
production section alone" — not the whole database): ran a script
against the real API (not raw SQL) so every snapshot/sequence/costing
rule stayed correct, adding 3 new styles, 6 new lots spanning all 8
lifecycle statuses, and activity on every previously-thin table:

| Table | Before | After |
|---|---|---|
| styles | 8 | 13 |
| production_lots | 28 | 36 |
| production_lot_sizes | **0** | 15 |
| production_stages | 117 | 138 |
| production_stage_entries | 11 | 22 |
| production_stage_challans | 12 | 19 |
| lot_additional_costs | 9 | 11 |
| fabric_processing_entries | 2 | 5 |
| internal_workers | 2 | 5 |
| material_issues | 2 | 5 |
| production_outputs | 7 | 12 |

All dates now reach through 2026-10-02/10-08 ("recent times"), up from
the prior max of 2026-09-07. One fabric processing entry was deliberately
left `in_process` (not completed) so the open-work view isn't empty.
Regression-checked all 4 Production frontend pages + a sample lot detail
page + its PDF report — all unaffected.

---

## "Upgrade #2" Phase 1 — Style ↔ Product/SKU Master Link (2026-10-02)

First phase of `docs/ERP upgrade after 07092026 call.md` "Upgrade #2"
(lines 505-1612, 39 sections — Garment ERP Style/Lot/Inventory
enhancements). Closed the foundational gap: `Style` had no FK to the
real `Product`/`ProductVariant` master at all, even though `StyleSize`/
`StyleColour` already correctly referenced the same `sizes`/`colours`
tables `ProductVariant` uses — so the size-chart/colour-selection half of
§3-4 (SKU/Variant Concept) was already built, but it never turned into
real sellable SKUs.

**Backend** (migration `034_style_product_link`, additive):
- `styles.product_id` (nullable FK → `products.id`). `create_style`
  auto-creates a new `Product` when none is supplied (`code=body.code or
  STY-<random>`, `product_type=finished_good`, carrying over
  `name`/`gender`/`season`); an explicit `product_id` links an existing
  one instead (company-scoped, 422 if not found/owned). `update_style`
  preserves the existing link when `product_id` is omitted, or relinks
  if a new one is given. `clone_style` always gets its own fresh
  auto-created product (never shares the source's) — consistent with
  cloning already resetting `code=None`.
- New `_ensure_variants()`: turns a Style's size × colour combinations
  into real `ProductVariant` SKUs under the linked product, in the exact
  `{code}-{SIZE}-{COLOUR}` format `add_variant` already used (extracted
  into a shared `build_variant_sku()` helper in the new
  `app/services/sku.py` so there's one SKU format, not two). Existence-
  checked so `update_style` can call it on every save without ever
  duplicating a variant. Found and fixed a real bug here during
  verification: the first version read `style.sizes`/`style.colours` off
  the already-identity-mapped ORM object, which still held the *old*
  collections from before `update_style`'s delete+reinsert — so adding a
  3rd colour produced 0 new variants instead of 2. Fixed by querying
  `StyleSize`/`StyleColour` fresh by `style_id` instead of trusting the
  relationship collection.
- `production_outputs.variant_id` (nullable FK → `product_variants.id`,
  additive) — lets a finished-goods receipt record the exact size/colour
  SKU; `ReceiveParams.variant_id` was already plumbed through
  `InventoryService.receive()`, so this was a pure passthrough.
- §34 (GST/HSN) substantially satisfied for any style with a linked
  product: `StyleDetailOut` now surfaces `product_code`/`hsn_id`/
  `gst_rate` resolved via `Style.product.hsn`, reusing the master's real
  GST/HSN rather than duplicating those fields onto `Style`.
- The 13 pre-existing styles (8 original + 5 from the Production
  backfill) were **not** retroactively linked — `product_id` stays
  `NULL` for them, consistent with this session's "never force-touch
  historical data" rule. Confirmed unaffected after migration.

**Frontend**: Style create/edit form gained an optional "Link to
Product" `SearchableSelect` (blank = auto-create) plus a linked-product/
GST readout in edit mode; Style detail page shows the linked Product
code + GST rate in the header badges; the lot detail page's Record
Output modal gained an optional Variant/SKU `SearchableSelect`,
populated from the chosen product's own `variants` (already returned by
`GET /products`, no new endpoint needed).

**Verification**: created a style with 2 sizes × 2 colours → 4 variants
auto-generated in the correct SKU format; added a 3rd colour via PATCH →
exactly 2 new variants, the original 4 untouched by ID (idempotency);
explicit `product_id` → no new Product created; clone → distinct new
Product; invalid `product_id` → clean 422; `ProductionOutput` with and
without `variant_id` both round-trip correctly. All test rows (3 styles,
2 products, 13 variants, 2 outputs) were cleaned up afterward, including
reverting the lot's `actual_qty` and recomputing the real product's
`cost_price` back to its correct pre-test value (the test outputs had
briefly skewed it via `_sync_product_pricing`'s per-lot rollup).
`tsc --noEmit` + full `next build` clean; regression-checked Styles
list/detail, Inventory Balance, Sales Orders, and Production Lots all
still 200.

**Next**: remaining "Upgrade #2" phases — Process Master, Size Chart
Master, Lot-level Trim/Packing snapshot + size-wise trim consumption,
Agent Master, Delivery Challan PDF, MIS return tracking, fabric receipt/
excess-delivery, weight-based cutting + piece↔kg conversion, fabric-first
enforcement, default-rate fallback, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 2 — Process Master (2026-10-02)

§1.1 (Size Chart Master) and §1.2 (Colour Master) were already satisfied
(Phase 1 confirmed `StyleSize`/`StyleColour` reference the real `sizes`/
`colours` tables). §1.3 (Process Master) was the real gap: `StyleProcess.
process_name` was pure free text, rendered as a plain `<Input>` in the
Style form — violating the standing "always SearchableSelect, never
free-text where a master exists" rule and the spec's explicit "Process
names should be selectable through a dropdown... configurable rather
than hard-coded" ask (12 named processes: Knitting, Dyeing, Compacting,
Printing, Cutting, Making, Fusing, Stitching, Trimming, Checking,
Ironing, Packing).

**Backend** (migration `035_process_master`, additive):
- New `process_masters` table (`company_id`, `name` UNIQUE per company,
  `default_unit`/`default_tolerance_pct`/`default_min_rate`/
  `default_max_rate`/`default_planned_rate`, `sort_order`, `is_active`),
  seeded with the 12 standard names for every existing company (mirrors
  Phase 8's "grant to every existing row" migration pattern) and added to
  `seed.py` for fresh installs.
- `style_processes.process_master_id` (nullable FK, additive). New
  `GET/POST/PATCH/DELETE /master/processes`, copying the existing
  `/master/sizes` CRUD block's shape exactly (same permissions, same 409
  conflict handling).
- `create_style`/`update_style` batch-fetch referenced `ProcessMaster`
  rows and fill `tolerance_pct`/`input_unit`/`output_unit`/`min_rate`/
  `max_rate`/`planned_rate` from the master's defaults **only where the
  incoming style-specific value is `None`** (§26: style-specific always
  wins) — also satisfies §1.3's "each process has its own rate/unit/
  tolerance" ask via a reusable default instead of re-entering it on
  every Style. "Supplier/worker/agent" and "insourcing/outsourcing" (also
  listed under §1.3) were deliberately **not** duplicated onto
  `ProcessMaster` — those are correctly LOT-time decisions already
  modeled on `ProductionStage` (`assignment_type`/`vendor_id`/
  `worker_id`), not a reusable Style-blueprint property.
- Found and fixed two real bugs during verification:
  1. `create_process`'s `ProcessMaster(...)` construction never set
     `created_at`, and since the SQLAlchemy model declares no Python-side
     default for that column (only the raw migration DDL has `DEFAULT
     now()`, invisible to the ORM), every INSERT sent an explicit `NULL`
     and failed the DB's `NOT NULL` — silently surfaced as a generic
     "Cannot create process" 409 instead of the real cause. Fixed by
     setting `created_at=datetime.now(timezone.utc)` explicitly in the
     endpoint.
  2. **A broader bug in `update_style` than Phase 1's fix covered**: the
     method's own returned `Style` object — not just `_ensure_variants`'
     internal query — was stale for every child collection (sizes,
     colours, yarns, fabrics, **processes**, trims, packing materials),
     because `get_style()` was called twice in the same session against
     the same already-identity-mapped object, and SQLAlchemy doesn't
     re-run `selectinload` eager loaders against collections an object
     already has loaded. Caught it concretely: a PATCH that set a
     process's `tolerance_pct` override to `1.0` (while linked to a
     master defaulting to `2.5`) echoed back `2.5` in the HTTP response
     even though the database correctly stored `1.0` — and a process
     meant to be deleted by the same PATCH still appeared in the
     response. Fixed with `self.db.expire(s)` right before the final
     re-fetch in `update_style`, forcing a real reload instead of
     trusting the pre-update in-memory snapshot. Re-verified Phase 1's
     colour-add scenario against this same fix — colours/processes now
     both reflect correctly in the PATCH response, not just the DB.

**Frontend**: `_style-form.tsx`'s process rows gain an optional "Process
(from master)" `SearchableSelect` next to the existing free-text name
input (kept, not replaced — same "add a link selector alongside the
existing field" pattern as Phase 1's Product link). Selecting a master
auto-fills the name (if blank) and any blank tolerance/unit/rate fields
from its defaults, never overwriting what the user already typed.

**Verification**: 12 processes seeded exactly once per company; created
a 13th custom process; built a Style with one master-linked process
(defaults correctly applied) and one fully custom process; confirmed
style-specific override beats the master default; confirmed clone
preserves `process_master_id`; all test rows (2 styles, 2 auto-created
products, 2 variants, 1 custom process, temporarily-set master defaults)
cleaned up afterward. `tsc --noEmit` + full `next build` clean; Docker
rebuilt; regression-checked Styles, Lots, Inventory Balance, Sales
Orders, and the Size/Colour master endpoints all still 200, style count
back to the correct 13.

**Next**: Size Chart Master UX pass (already structurally present via
`StyleSize`, §1.1's "quantity applicable for each size" needs a closer
look), Lot-level Trim/Packing snapshot + size-wise trim consumption,
Agent Master, Delivery Challan PDF, MIS return tracking, fabric receipt/
excess-delivery, weight-based cutting + piece↔kg conversion, fabric-first
enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 3 — Size Chart Master (2026-10-02)

§1.1 asks for a reusable **Size Chart Master**: a named chart grouping
multiple sizes, each with its own quantity, *"configurable and reusable
from Style Creation."* Previously `StyleSize` had no quantity field at
all and no chart concept — sizes were picked one at a time from the flat
`Size` master with nothing to reuse across styles. The "reusable from
Style Creation" half had nowhere to land either: `ProductionLotCreate.
sizes` already existed server-side (`create_lot` wrote
`ProductionLotSize` rows from it), but the Lot-creation frontend modal
never collected or sent `sizes` at all — so `ProductionLotSize.
planned_qty` was fully dead on the UI side.

**Backend** (migration `036_size_chart`, additive): new `size_charts`/
`size_chart_items` tables (named chart + per-size quantity, unique name
per company); `style_sizes` gains `quantity`/`size_chart_id`.
`create_style`/`update_style` batch-fetch referenced chart items and
fall back to the chart's quantity only when the style-specific value is
`None` (style-specific always wins — same §26 rule as Phase 2's Process
Master); `clone_style` carries `quantity`/`size_chart_id` through
unchanged (unlike `product_id`, which deliberately gets a fresh one on
clone — sizes/quantities are data to copy, product identity is not).
`create_lot` now eager-loads `Style.sizes` and, when the caller sends no
explicit `sizes`, auto-populates `ProductionLotSize.planned_qty` from
the Style's quantities — the first real implementation of "reusable from
Style Creation." New `GET/POST /production/size-charts`,
`PATCH/DELETE /production/size-charts/{id}`, mirroring the Style routes'
shape exactly, including applying Phase 2's `self.db.expire()` fix
proactively in `update_size_chart` so the same staleness bug couldn't
recur here.

**Also closed a gap left by Phase 2**: discovered mid-phase that a
generic, config-driven Master Data admin page already exists
(`/admin/master-data`, tabs for Categories/Sizes/Colours/Units/
Warehouses/HSN) that Phase 2's Process Master should have used instead
of shipping with zero admin UI. Process Master's fields are flat (name +
5 default rate/unit values), so it dropped straight into this existing
generic component as one more config entry — no new component code,
just a config addition, now exposing `/master/processes` CRUD in the UI
for the first time.

**Frontend**: new `/production/size-charts` page (list + create/edit
modal with size+quantity rows) — a dedicated page rather than folded
into the generic admin table, because a chart is a *named, grouped*
entity (closer to Style's own shape) and the generic component only
supports flat fields. `_style-form.tsx`'s Sizes section gained a "Load
from Size Chart" selector (merges sizes + seeds quantities, overridable)
and a per-selected-size quantity input list (previously no quantity
input of any kind existed in this form). The Lot-creation modal
(`lots/page.tsx`) now fetches the selected style's sizes/quantities and
renders an editable per-size planned-qty list, finally sending `sizes`
in the create payload.

**Verification**: created a chart (S=100/M=150/L=120); built a Style
loading it with M overridden to 200 → confirmed S=100 (fallback),
M=200 (override), L=120 (fallback); updated the chart's L to 130 and
confirmed the *existing* Style's L stayed at 120 (historical snapshot
intact) while a *new* style loading the chart got 130; created a Lot
with no explicit sizes → `ProductionLotSize` rows correctly defaulted
to 100/200/120; created a second Lot with an explicit size override →
confirmed the override replaced the defaults rather than merging.
Cleanup required deleting through a 3-level FK chain (lot sizes → stage
entries → stages → lots) learned the hard way when a multi-statement
`psql -c` call's implicit transaction silently rolled back partial
deletes on a later failure — redone as one correctly-ordered atomic
call. `tsc --noEmit` + full `next build` clean (new `/production/
size-charts` route confirmed in the build output); Docker rebuilt;
regression-checked styles (13), lots (36), size-charts (0, clean),
`/master/processes`, Inventory Balance, and Sales Orders all back to
correct state and 200.

**Next**: Lot-level Trim/Packing snapshot + size-wise trim consumption,
Agent Master, Delivery Challan PDF, MIS return tracking, fabric receipt/
excess-delivery, weight-based cutting + piece↔kg conversion, fabric-first
enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 4 — Lot-level Trim/Packing Snapshot + Size-wise Trim Consumption (2026-10-02)

§21's key sentence: *"\[size-wise trim consumption\] should be fetched
automatically when the Production Lot is created."* Previously
`StyleTrim.quantity` was a single flat value with no per-size breakdown
anywhere — even though `StyleTrim.category` already distinguished
`"Sizable"` vs `"Non-Sizable"`, neither category actually behaved
differently. Neither trims nor packing materials were ever snapshotted
onto a `ProductionLot` at all (only `StyleAdditionalCost` had that
planned/actual pattern, via `LotAdditionalCost`). `Style.pieces_per_box`
was stored and snapshotted but nothing ever divided by it — no "boxes
required" calculation existed despite §23 asking for one.

**Backend** (migration `037_lot_trim_packing_snapshot`, additive): new
`style_trim_sizes` (optional per-trim size-wise quantity, meaningful
when `category = 'Sizable'`); new `lot_trims`/`lot_packing_materials`
(LOT-level snapshot, planned/actual split, mirroring
`lot_additional_costs`'s existing shape). `create_lot` now snapshots
every Style trim/packing material at creation time: a `"Sizable"` trim's
`planned_qty` sums `size_breakdown.quantity × that size's resolved
ProductionLotSize.planned_qty` (direct reuse of Phase 3's now-real
per-size data); a flat trim or packing material scales off the LOT's
total `planned_qty`; both apply `excess_pct` when set. New `PATCH
/lots/trims/{id}` and `PATCH /lots/packing/{id}` to record actual
consumption, mirroring the existing additional-costs actual-amount
endpoint exactly. `boxes_required` is a pure derived value
(`ceil(actual_qty / pieces_per_box)`), not a stored column, so it always
reflects the LOT's current output rather than a stale snapshot.
`clone_style` carries trim `size_breakdown` through.

**Frontend**: Style form's Trim rows show a per-size quantity row list
when a trim's category is `"Sizable"` (reusing the Style's own already-
selected sizes); the flat Qty field stays as the fallback for when no
size-wise values are filled in. Lot detail page gained "Trims" and
"Packing Materials" Cards (planned/actual side by side, inline "record
actual" action copying the existing Additional Costs Card's pattern) and
a "Boxes Required" badge.

**Verification**: Style with a Sizable trim (Button: S=4/M=4/L=5/XL=5)
and a Non-Sizable trim (Label: flat qty=1) + a Carton packing material
(qty=1, excess 5%); Lot with per-size plan S=100/M=100/L=50/XL=50
(total 300) → confirmed `LotTrim.planned_qty`: Button = 4×100+4×100+
5×50+5×50 = **1300** exactly, Label = 1×300 = **300** exactly;
`LotPackingMaterial.planned_qty` = 1×300×1.05 = **315** exactly. Actual-
qty PATCH endpoints round-trip correctly without touching planned
values. `boxes_required` computed correctly (0 when `actual_qty` is
still 0, confirmed non-null once `pieces_per_box` is set — not the
"unset" case). Clone preserved the trim's `size_breakdown`. `tsc
--noEmit` + full `next build` clean; Docker rebuilt; regression-checked
all 37 lots list without error (eager-load fix verified across every
pre-existing lot with zero trims/packing rows, not just the new test
one); styles/lots/size-charts/processes/inventory/sales all back to
correct state and 200 after cleanup.

**Next**: Agent Master, Delivery Challan PDF, MIS return tracking,
fabric receipt/excess-delivery, weight-based cutting + piece↔kg
conversion, fabric-first enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 5 — Agent Master Wiring (2026-10-02)

§16 names Supplier/Customer/Worker/Agent as entities that must come from
a real master, never free text. Research found **Agent master data
already fully existed** — `Vendor.vendor_type` already accepts `"agent"`
(validated in `VendorCreate`), and `/purchase/vendors` already has a
complete admin page with an "Agents" filter tab. No new master table was
needed; building one would have duplicated the Vendor master the spec
itself warns against.

The real gap, found by reading all three places an Agent Commission line
can be created: `party_vendor_id` had **no UI path to ever be set,
anywhere in the app**. The Style form had no Additional Costs section at
all (even though the backend and the Style detail page's read-side both
fully supported it); the Lot-creation modal's cost rows had no vendor
field; the Lot detail page's "Add Cost" modal had no vendor field
either. Every Agent Commission line created through the UI silently had
its agent unset — the only way to populate it was a raw API call.

**Pure frontend phase — no backend changes needed** (every field
already existed end-to-end in `StyleAdditionalCostIn/Out`,
`LotAdditionalCostCreate/Out`, and the services). Added: a new
"Additional Costs & Agent Commission" section to `_style-form.tsx`
(cost type toggle, description, amount, basis, and an Agent
`SearchableSelect` that only renders for `cost_type=agent_commission`,
filtered server-side via the `/purchase/vendors?vendor_type=agent` param
the Vendors page itself already uses); the same vendor field added to
`lots/page.tsx`'s `AddLotModal` cost rows and to `lots/[id]/page.tsx`'s
`AddLotCostModal`.

**Verification**: created a throwaway Agent and a throwaway Supplier
vendor, confirmed `?vendor_type=agent` returns only the Agent; created a
Style with an Agent Commission cost referencing the real agent →
`party_vendor_id` persisted; created a Lot from that Style → the
snapshotted `LotAdditionalCost.party_vendor_id` carried through
unchanged; posted directly to `/lots/{id}/additional-costs` (what
`AddLotCostModal` calls) with an agent → persisted correctly. All three
write paths now actually set what was previously only ever readable.
`tsc --noEmit` + full `next build` clean; Docker rebuilt; regression-
checked styles/lots/size-charts/vendors/inventory/sales all 200; test
styles/lots/vendors cleaned up, counts back to 13 styles / 36 lots.

**Next**: Delivery Challan PDF, MIS return tracking, fabric receipt/
excess-delivery, weight-based cutting + piece↔kg conversion, fabric-first
enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 6 — Delivery Challan PDF (2026-10-02)

§17 asks that a Delivery Challan be generated automatically whenever
material goes outward for job work, and be viewable by the user,
containing DC Number/Date/From/To/Product-Style/Process/Lot/Quantity/
HSN/Value. The data (`ProductionStageChallan`) already existed in full;
it just had no document view anywhere — only ever rendered as a row in
the Lot detail page's challan list.

**Backend**: new `templates/delivery_challan.html` + `services/
delivery_challan.py` (`render_delivery_challan_pdf`/
`delivery_challan_filename`), copying `packing_slip.py`'s exact
WeasyPrint-over-Jinja2 shape — the third PDF document in this app, same
pattern each time, no new library. New `GET /production/stages/
challans/{id}/delivery-challan.pdf?preview=bool` with the same
inline/attachment convention as the existing Lot Report PDF endpoint.
New `ProductionService.get_challan_for_document()` loads the challan's
full `stage → lot → style → product → hsn` chain — HSN/GST comes from
the Style's linked Product (Phase 1), never duplicated onto the challan
itself. Value is `bill_amount` when billed, else `rate_per_pc ×
out_qty` labeled "(Estimated)" so the document never implies a final
figure before one exists.

**Frontend**: a small Download icon added to each `ChallanRow` in the
Lot detail page, reusing the exact blob-download pattern already
written for the Lot Report PDF button.

**Verification**: generated real PDFs (via `pdftotext`) for a
vendor-assigned challan with `bill_amount` set (Value showed the exact
billed figure, no "Estimated" suffix), a worker-assigned challan
(confirmed "To" showed the worker's name labeled "Internal Worker", not
a vendor), and an unbilled challan (Value showed `rate_per_pc × out_qty`
= 1.00 × 440 = ₹440.00, hand-verified against the DB, correctly labeled
"Estimated"). Built a throwaway Style (auto-linked Product), set its
product's HSN, created a Lot/Stage/Challan from it → confirmed HSN
"5509" rendered correctly end-to-end through the Style→Product→HSN
chain; the 13 pre-existing styles (no product link) correctly show "—"
for HSN. Confirmed `preview=true` → inline, omitted → attachment, with
the right filename both times. `tsc --noEmit` + full `next build`
clean; Docker rebuilt; regression-checked the pre-existing Lot Report
PDF endpoint still works (same WeasyPrint/Jinja environment, no
cross-contamination) plus styles/lots/size-charts/vendors/inventory all
200; test style/lot/stage/challan cleaned up, counts back to 13/36.

**Next**: MIS return tracking, fabric receipt/excess-delivery,
weight-based cutting + piece↔kg conversion, fabric-first enforcement,
configurable bill-alert threshold.

---

## "Upgrade #2" Phase 7 — MIS Return Tracking (2026-10-02)

§19 asks that unused material remaining after a production process be
returnable to inventory, recording Issued/Used/Returned/Wastage/
Recoverable-Resale; §18 asks that a partial remainder stay open, never
silently treated as complete. `MaterialIssueItem` only tracked
`planned_qty`/`issued_qty` — Used, Returned, and Wastage had no fields
anywhere, and nothing ever physically returned material to inventory.

**Backend** (migration `038_mis_return_tracking`, additive):
`material_issue_items` gains `used_qty`/`returned_qty`/`wastage_qty`/
`return_notes`/`return_inv_transaction_id`. New `ProductionService.
record_mis_item_return()`: validates `used + returned + wastage ≤
issued_qty` (raises `QuantityValidationError` → 422 otherwise — the
concrete form of §18's "never treat an inconsistent remainder as
complete"), then posts only the **delta** of any `returned_qty`
increase through `InventoryService.receive()` with
`reference_type="mis_return"` — the exact inverse of `create_mis`'s
existing `InventoryService.issue()` call, same unified-inventory
principle (§13), no new movement mechanism. "Recoverable/Resale" isn't
a separate flag: a quantity that's actually posted back into real,
usable warehouse stock *is* what recoverable/resalable means. New
`PATCH /production/mis/items/{id}/return`. `_mis_item_out`/`_mis_out`
(previously sync) became `async` to resolve `product_name`/
`unit_abbreviation` — MIS items had never shown a readable product
name before, only a raw UUID.

**Frontend**: the Lot detail page's "Material Issues" card previously
showed only a one-line summary per MIS slip with zero item-level
detail. Expanded each slip to list its items (product name, Issued/
Used/Returned/Wastage) with a "Record Return" action opening a small
modal (Used/Returned/Wastage/Notes, live running-total warning when it
would exceed Issued) that `PATCH`es the new endpoint.

**Verification**: issued item (320 kg) → recorded Used=200/Returned=100/
Wastage=20 (sums to exactly 320) → confirmed the warehouse's real stock
balance for that product increased by exactly 100 (80→180 kg, checked
via the Stock Balance endpoint, not just the MIS record). Attempted
Used=250/Returned=100/Wastage=20 (370 > 320) → 422 with a clear message.
Increased Returned from 100→130 → confirmed only the delta (30) posted
as a new inventory transaction, balance went 180→210, not a duplicate
130. Cleaned up by deleting the two test inventory transactions and
resetting the item's return fields — balance correctly back to 80.
`tsc --noEmit` + full `next build` clean; Docker rebuilt; regression-
checked styles/lots/mis/size-charts/vendors/inventory plus both PDF
endpoints from Phases 4 and 6 (confirming the `_mis_out` async refactor
didn't disturb the shared production endpoints file); counts unchanged
at 13 styles / 36 lots throughout since this phase only touched an
existing item's return fields, not new styles/lots.

**Next**: fabric receipt/excess-delivery, weight-based cutting + piece↔kg
conversion, fabric-first enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 8 — Fabric Receipt / Excess Delivery (2026-10-02)

§6: *"If a fabric supplier delivers more quantity/weight than planned,
the excess must be recorded rather than silently ignored."* §4's "Feeder
must become GSM" and "Yarn optional on Lot" were checked directly and
found already fully compliant (no `feeder` field exists anywhere;
`ProductionLotCreate` has no yarn field at all) — no work needed there.

The excess-delivery gap turned out bigger than a missing column:
`PurchaseOrderItem.ordered_qty`/`received_qty` and `PurchaseEntryItem.
po_item_id` already existed in the schema, but the GRN creation page
**never offered PO selection at all** — confirmed by direct read, no
`purchase_order_id`/`po_item_id` anywhere in that file. Every GRN
created through the UI had no PO link, so there was no "planned"
baseline to ever compare against — the same "backend field, zero UI
path" pattern already found and fixed three times this session (Style↔
Product, Agent Commission, Lot sizes-from-Style). Fixed the whole path,
not just the column.

**Backend** (migration `039_grn_excess_delivery`, additive):
`purchase_entry_items` gains `excess_qty`. `create_purchase_entry`
computes it per item, when `po_item_id` is set, as the delta
`max(0, new_cumulative − ordered_qty) − max(0, old_cumulative −
ordered_qty)` computed before updating the PO item's running
`received_qty` — a delta, not a flat `qty > ordered` check, so a second
over-delivery against an already-exceeded PO item doesn't double-count
the whole thing as "excess" again. Purely recorded, never rejected (the
spec says "recorded," not "blocked" — deliberately unlike the earlier,
already-shipped Sales-Order-vs-customer-PO tolerance phase, which does
reject).

**Frontend**: `purchase/grn/page.tsx`'s `AddGRNModal` gained an optional
Purchase Order selector (filtered to the chosen vendor,
approved/partial status); selecting one pre-fills item rows from the
PO's items with `po_item_id` attached, each showing "Ordered: X ·
Received so far: Y" and a live excess preview as the user edits
`accepted_qty`. Manual (no-PO) rows are unchanged. The GRN list gained
an "Excess" flag badge per entry, mirroring the exact pattern MIS
already uses for its own excess flag.

**Verification**: PO for 100 kg → GRN for 105 → `excess_qty=5`, PO
`received_qty=105`. A second GRN for 10 more against the same (already
over-received) PO item → `excess_qty=10` (all of it, proving the delta
formula rather than double-counting). A GRN item with no `po_item_id` →
`excess_qty` stayed `None`. A GRN fully within the ordered quantity
(90 of 100) → `excess_qty=0`, never negative. Confirmed the GRN list
correctly flags only the two over-delivered entries as "Excess."
`tsc --noEmit` + full `next build` clean; Docker rebuilt; regression-
checked styles/lots/mis/vendors/purchase-orders/inventory and the
Delivery Challan PDF endpoint. Cleanup required deleting through the
GRN→inventory-transaction→PO chain atomically (items → transactions →
entries → PO items → POs, no cascades anywhere in this chain) — stock
balance confirmed back to exactly its pre-test state (the test's
temporary kg-denominated balance row disappeared entirely once its sole
transaction was removed).

**Next**: weight-based cutting + piece↔kg conversion, fabric-first
enforcement, configurable bill-alert threshold.

---

## "Upgrade #2" Phase 9 — Weight-based Cutting + Piece↔Kg Conversion + Tolerance/Gain-Loss (2026-10-02)

§9 asks Cutting to track input/output weight and split the remainder
into Wastage vs. Recoverable/Resale ("the exact classification should be
recorded rather than losing the balance"); §10 asks for automatic piece↔
kg rate conversion; §11/§12 ask for a configurable tolerance (default
3%) and a clear Within/Above-tolerance gain/loss classification.

`ProductionStageEntry` was purely piece-based before this phase — no
weight fields at all. `ProductionStage.tolerance_pct` already existed,
already snapshotted from `StyleProcess.tolerance_pct` at LOT creation —
but nothing had ever compared actual output against it; the tolerance
was stored and never used. `DEFAULT_WASTAGE_PCT = Decimal("3")` already
existed in the cost-summary code, exactly matching §11's "general
default: 3%" — reused here rather than reinvented.

**Backend** (migration `040_weight_based_cutting`, additive):
`production_stage_entries` and `production_stages` both gain
`input_weight_kg`/`output_weight_kg`/`wastage_kg`/`recoverable_kg` — the
entry columns are opt-in per logged session, the stage columns are
rollup totals, mirroring exactly how `input_qty`/`output_qty` already
roll up. `add_stage_entry` validates `wastage_kg + recoverable_kg ≤
input_weight_kg − output_weight_kg` per entry (same
`QuantityValidationError` pattern as the existing output>input piece
check right above it in the same method — §9's "never lose the
balance"). `_stage_out` computes (never stored, like `accepted_qty`
already is): `expected_output_kg = input × (1 − tolerance/100)`,
`variance_kg = output − expected`, `permitted_tolerance_kg`,
`within_tolerance = variance_kg ≥ 0`, `weight_per_piece = output_weight_kg
÷ output_qty`, and `effective_rate_per_kg = rate_per_pc × (output_qty ÷
output_weight_kg)` — §10's exact "₹100 per 500g → ₹200 per kg" worked
example, computed from the stage's own real rate and weight rather than
a separate abstract conversion master.

**Frontend**: `AddEntryModal` (Lot detail page) gained an optional
"Weight Tracking (kg)" section (Input/Output/Wastage/Recoverable),
available on any stage, not gated by stage type. The stage card gained
a conditional row — shown only once weight has ever been logged —
with Input/Output weight, a Within/Above-tolerance badge, Weight/Piece,
and the derived ₹/kg rate.

**Verification**: logged Input=100/Output=65/Wastage=15/Recoverable=20
(sums to exactly 100) on a real Cutting stage with no explicit
tolerance set → confirmed the 3% default kicked in:
`expected_output_kg=97`, `variance_kg=-32`, `permitted_tolerance_kg=3`,
`within_tolerance=false` — matching §12's own worked example exactly in
shape. On a second stage, logged Input=100/Output=97 (exactly at the
3%-tolerance boundary) → `variance_kg=0`, `within_tolerance=true`,
confirming the flip at the exact boundary. With `output_qty=100,
output_weight_kg=65` → `weight_per_piece=0.65`; with `rate_per_pc=100` →
`effective_rate_per_kg≈153.85`, hand-verified (`100 × 100/65`). Attempted
Wastage(10)+Recoverable(0) exceeding a 5kg remainder → 422 with a clear
message. A stage with no weight ever logged → all new computed fields
`None`, no crash. `tsc --noEmit` + full `next build` clean; Docker
rebuilt; regression-checked styles/lots/mis/purchase-entries/inventory
plus the Delivery Challan PDF endpoint. Both test stages (pre-existing,
borrowed from the Production backfill) fully reverted to their original
`pending` state with zero quantities afterward — not deleted, since they
belonged to real seeded lots.

**Next**: none in the Upgrade #2 list — all 39 sections addressed or verified as satisfied (see Phase 11).

---

## "Upgrade #2" Phase 10 — Fabric-First Enforcement (2026-10-03)

§33: garment production must not begin without the required fabric
stock/configuration. Confirmed by reading code: nothing gated it, and
`create_mis` auto-advances a lot to `in_production` on *any* material
issue (yarn or trims included), so lot status could not be trusted as a
fabric signal.

**Rule** (`BusinessRulesEngine.validate_fabric_ready`, pure logic): a
lot whose style has a fabric configuration is ready when fabric has been
issued to the lot (MIS items on `product_type == "fabric"` with qty > 0),
or — for `fabric_source == "yarn"` styles only — a `FabricProcessingEntry`
is `completed`. Lots without a style are not gated.

**Enforcement point**: the first garment *piece* entering a stage
(`add_stage_entry` with `pieces_in > 0`) and a job-work challan sending
garments out (`create_challan` with `out_qty > 0`). Gating at those points
cannot be bypassed via MIS auto-advance. Rejects with
`BusinessRulesError` → 422 `{code: fabric_not_ready, message}`. Zero-piece
logs are not blocked.

**Visibility**: `ProductionLotOut.fabric_blockers` lists the outstanding
reasons; the lot detail page shows them in a banner above the stages.

**Frontend fix found along the way**: several modals (stage entry,
send-to-vendor, MIS return, issue material) read `error` as a string,
but business-rule errors use `{code, message}`, so the real reason was
silently replaced by a generic fallback. Added a `parseApiError` helper to
the lot page and used it in those modals.

**Historical data**: existing lots are not retroactively blocked; the
gate applies to new garment entries/challans. Backfilled lots with no
fabric issued will be blocked from new garment entries until fabric is
issued or processed — intended per §33.

**Verification** (on throwaway styles/lots, cleaned up afterward):
- yarn style with no `StyleFabric` rows → 422 "Style has no fabric
  configured"; `fabric_blockers` reports the same.
- configured yarn style, nothing issued/processed → 422 yarn message.
- purchased style, configured, nothing issued → 422 "No fabric issued".
- after issuing 10 kg of a fabric-type product to the lot → the same
  entry returns 201, blockers empty.
- yarn style with a completed fabric processing entry (no fabric MIS) →
  201.
- lot without a style → entries unaffected (201); zero-piece entry
  allowed.
- challan with `out_qty > 0` on an unready lot → 422.

`tsc --noEmit` and `npm run build` pass; containers rebuilt; regression
checks (styles, lots, MIS, purchase entries, inventory balance, lot detail
page) all 200. Test data removed in one transaction; counts back to 13
styles / 36 lots.

---

## "Upgrade #2" Phase 11 — Configurable Bill / Invoice Alert Threshold (2026-10-03)

§32: alert when material is sent to an outsourced process and the vendor's
bill is not received within a configurable number of days.

The alert already existed (`check_job_work_challans`, daily Celery task,
`job_work_bill_pending`), but its window was hardcoded to 7 days and it
only looked at challans already *received*, so material still out was
never flagged.

**Changes**
- `companies.bill_alert_days` (migration `041_bill_alert_days`, default 7,
  1–365 validated in `CompanyUpdate`), exposed through the existing
  `GET/PUT /admin/company` and an input on the admin company settings page.
- The task now compares `COALESCE(in_date, out_date)` against each company's
  own window, and includes `out` as well as `received` challans. Cancelled
  and bill-received challans are excluded. Grouping, notification type and
  publish are unchanged; body text now says "dated" rather than "received",
  since out challans have no in-date yet.

**Verification**: `PUT` 3 → 200, `PUT` 0 → 422. The task run at 3 days
alerted 5 challans, matching a direct SQL count of the same predicate. An
out-status challan was included. Sensitivity: 20 days → 5 alerting, 30 days
→ 0. Restored to 7; the two test notifications generated during the runs
were removed. Type checks, the frontend build, and the page/API regression
checks pass.

---

## End-to-End Test Pass × 2 + Bug Fixes (2026-10-03)

Two complete passes (runs A and B, 109 write/read steps each) over the
Production, Purchase, Sales, Inventory, Master, and Admin flows, driven
through the same endpoints the UI buttons call. Browser click-through was
not available in this session, so button wiring was covered by an
endpoint audit: all 80 GET routes respond without 5xx, and all 343 frontend
API call sites were matched against backend routes.

**Bugs found and fixed**
1. **Backend fails to start on restart** (`app/db/seed.py`). The seed
   inserted a new "My Apparel Company" on every start (no unique constraint)
   and bound to an arbitrary `LIMIT 1` company, which could be a stale
   duplicate with no admin user, then crashed on a missing
   `ADMIN_SEED_PASSWORD`. Now it binds to the company that owns the admin
   user and inserts only when none exists. Company count held steady across
   restarts after the fix.
2. **Stage update rejected unrelated edits** (`update_stage`). Sent/received/
   rejected validation ran on every save, so an in-house stage with
   rejections from its entries could not have its rate or name edited. It
   now runs only when those quantities change, and only for outsourced stages.
3. **Administrator lacked `production.delete`** (used by size-chart delete,
   added in Phase 3). Migration `042_grant_production_delete` grants it, and
   the seed list includes it for fresh installs.
4. **Invoices under-billed GST** when created from a delivery. The delivery
   line totals carry no tax and the order's tax was ignored. Tax is now
   pro-rated from the matching order lines by delivered quantity. Verified:
   SO 2250 + CGST 56.25 + SGST 56.25 = 2362.50, and the invoice now matches.
5. **Topbar global search product results never appeared.** It called
   `/inventory/products`, which doesn't exist; `allSettled` hid the failure.
   Now uses `/products`.
6. **CRM leads page customer picker** requested `/api/v1/sales/customers`
   with the prefix doubled by the client base URL. Fixed.
7. **WhatsApp "link to lead" button** sent a PATCH the backend didn't
   implement. Added `PATCH /whatsapp/contacts/{id}`, which only accepts leads
   from the same company (422 otherwise, 404 for unknown contacts).

**Verified correct, no change needed**: GRN excess (105 against 100 gives
5), fabric balance across warehouses (GRN +105 included), trim and packing
planned quantities (Button 460 = 4×40 + 5×60; Carton 105 = 1×100×1.05),
lot size splits, delete of an in-use size chart (409 guard), and the
fabric-first gate in both directions.

**Left in place**: test records prefixed `QAA`/`QAB` (plus an earlier
partial `QA1`) remain in the dev database; the run scripts are in the
session scratchpad.

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

---

## Dropdown Unification — SearchableSelect Everywhere (2026-10-03)

All dropdowns in the frontend now use the shared `SearchableSelect` (`frontend/src/components/shared/searchable-select.tsx`), per the project rule against native `<select>`.

| Change | File |
|---|---|
| Master-data inline field dropdown (`FieldInput` options branch) switched from native `<select>` to `SearchableSelect`, accent `INDIGO`, width class moved to a wrapper div | `frontend/src/app/(app)/admin/master-data/page.tsx` |
| Removed unused native `Select` export (no importers) | `frontend/src/components/create/ModalShell.tsx` |

Verification:
- Scan: no native `<select>` remains under `frontend/src`.
- `npx tsc --noEmit`: exit 0.
- `npm run build`: exit 0.
- `docker compose build frontend && docker compose up -d frontend`: rebuilt; `/`, `/admin/master-data`, `/admin/company`, `/production/lots`, `/production/size-charts` respond (307 on `/`, 200 on the rest).

---

## CRM SMTP Connection Test Fix (2026-10-03)

Symptom: "SMTP test failed: Error connecting to https://smtp.gmail.com on port 587: Name or service not known".

Causes:
1. The saved host was `https://smtp.gmail.com`. The host field expects a bare hostname, so DNS lookup failed.
2. `use_tls=True` was passed straight to aiosmtplib. That means implicit TLS, which only fits port 465. Port 587 needs STARTTLS.

Fix (`backend/app/api/v1/endpoints/crm.py`):
- `_smtp_transport_kwargs(cfg, password)` is a shared helper used by both the test and send paths. It strips `http(s)://`, `smtp(s)://` and any path from the host. Port 465 uses implicit TLS; other ports use STARTTLS when encryption is enabled.
- Existing saved configs work without re-saving.

Verification: `POST /crm/email/smtp-config/test` returns 200 "Test email sent successfully" against the saved Gmail config (587, STARTTLS). `is_verified` is now set.

### SMTP test result display (follow-up, 2026-10-03)

The email was delivered, but the CRM settings page showed "Unknown result". The success response has `data: null` and the page read `data.data`. Failures read `detail`, while the app's error envelope uses `error`. The test mutation in `frontend/src/app/(app)/crm/settings/page.tsx` now shows the backend's `message` on success and the `error` string on failure. `tsc --noEmit` passes and the frontend container is rebuilt.

### Email templates for every CRM category (2026-10-03)

Eight active templates, two per category, created through `POST /crm/email-templates`: intro (enquiry received, company overview), follow-up (no response, after meeting), quote (price quotation, revised quotation), closing (order confirmed, thank you). Bodies are plain text with no merge tags, because the send path does no placeholder substitution.

### Date pickers and range filters unified (2026-10-03)

Native `<input type="date">`, `datetime-local` and the bordered from/to range box are replaced everywhere with shared components in `frontend/src/components/shared/date-picker.tsx`:

- `DatePicker`: form field look. The calendar header has month and year buttons. Clicking the year opens a 12-year grid, so any year is one click away. Clicking the month opens a month grid. Datetime mode adds an hour/minute row. Supports min/max, required and disabled. Values stay `YYYY-MM-DD` or `YYYY-MM-DDTHH:mm`, the same as native inputs.
- `DateRangeFilter`: the preset pills (30D / 90D / YTD / All, or a page-specific list) and the from/to pickers share one muted group, styled like the report filters. The active preset is highlighted by comparing against local calendar dates.

Coverage: 33 files. The ad-spend page, the four report pages and the CRM reports page use `DateRangeFilter`. The CRM reports page no longer has an Apply button; picking a date or preset applies it immediately, as on the other report pages. The lead detail "Expected Close Date" saves when a date is picked instead of on blur. The local-date fix also removes the UTC `toISOString()` day shift for presets and default ranges.

Verification: `tsc --noEmit` and `npm run build` pass, the frontend container is rebuilt, and the affected routes return 200. The calendar popup has not been clicked through in a browser.

### 2FA login: wrong code burned the session (2026-10-03)

Symptom: "Invalid or expired 2FA code" even with the exact code from the authenticator app.

Cause: `consume_pending_2fa` deleted the pending login session on every attempt, including wrong codes. After one wrong code, every retry got "2FA session expired", and the login page showed the same generic message for both cases. The stored TOTP secret and `verify_totp` were checked and are correct.

Fix:
- `backend/app/core/security.py`: `get_pending_2fa` (non-consuming), `record_failed_2fa` (counts wrong codes, 5-minute window), `clear_pending_2fa` (on success or after `PENDING_2FA_MAX_FAILURES` = 5 failures).
- `backend/app/api/v1/endpoints/auth.py`: `verify_2fa_login` keeps the session across wrong codes and returns the real reason.
- `frontend/src/app/(auth)/login/page.tsx`: shows the backend message; returns to the password step when the session has ended.

Verification in the backend container: a wrong code returns 401 with the specific message, the correct code returns 200 with a token, and replaying the used session returns 401.

### Permission-based module hiding and 403 handling (2026-10-03)

Symptom: a user without `inventory.view` still saw Inventory in the sidebar, and clicking it sent them back to the login page.

Causes:
1. The sidebar showed every module, regardless of permissions.
2. The API client treated any "Permission required" 403 as a stale session. It tried a token refresh and, if that failed, cleared the token and redirected to `/login`. Concurrent requests also each tried to rotate the same refresh token, so the first rotation revoked the rest.

Changes:
- `frontend/src/lib/permissions.ts` (new): `usePermissions()` reads `/auth/me` and exposes `can(permission | any-of list)`.
- `frontend/src/components/layout/module-nav-config.tsx`: each module declares its permission (`crm.view`, `sales.view`, `purchase.view`, `inventory.view`, `production.view`, `finance.view`, `reports.view`, admin any-of).
- `frontend/src/components/layout/app-sidebar.tsx`: shows only permitted modules. The Create button is hidden when no quick-create item is allowed.
- `frontend/src/components/create/CreateMenu.tsx`: quick-create items need `production.create` or `inventory.create`.
- `frontend/src/app/(app)/layout.tsx` + `frontend/src/components/layout/access-denied.tsx` (new): a typed URL for a module the user cannot access shows an access-denied panel.
- `frontend/src/lib/api.ts`: one shared token refresh for concurrent requests. A permission 403 never logs the user out. Only a 401 whose refresh fails redirects to login.
- Login and logout clear the cached permissions, so a different account on the same tab does not inherit them.

Scope: module-level hiding. Individual CRM create and edit buttons are not yet hidden for users without `crm.create` or `crm.edit`; the backend still rejects those actions.

Verification: `tsc --noEmit` and `npm run build` pass, and the frontend container is rebuilt. For kishore.m@gmail.com the database confirms `inventory.view` is absent and `crm.edit` and `crm.create` are absent. The sidebar behaviour has not been clicked through in a browser.

### Role-based access test matrix (2026-10-03)

Test user `qa.tester@example.com` (role "QA Permission Tester") was created on a throwaway copy of the database, `apparel_erp_qa`, so the dev data was not touched. The copy has been dropped.

Method: for every permission, two scenarios were run, "only this permission" and "all except this permission". The token was refreshed after each role change, so each check used the real permission set. Each write endpoint was called with a schema-valid body, and the response was compared with the required permission: 403 "Permission required" exactly when the permission is missing.

Result: 150 scenarios, 20,475 checks passed, 0 failed, 975 inconclusive (the generated body failed validation, so the permission check was not reached).

Not covered by the API matrix (excluded because they send real messages or call external services): SMTP send and test, CRM email send, WhatsApp send/webhook/templates, the AI assistant chat, forgot-password, change-password, logout, and 2FA setup/enable/disable.

Known backend gap: the WhatsApp send endpoints do not check a permission.

Frontend: sidebar modules, create/edit routes and action buttons are hidden for users without the matching permission. Verified by typecheck and build; not clicked through in a browser.

Incident: the first matrix run used a copy with the live SMTP settings, and about 65 test emails were sent. The copy's SMTP settings are now removed before any run.

### CRM end-to-end test, two passes (2026-10-03)

Script: a flow test of 102 steps covering lead sources, tags, products, customers, organizations, persons and notes, leads (create, edit, stage, status, assign, products, bulk actions, kanban, history), activities, tasks, quotes (create, edit, status, duplicate, delete), email templates, WhatsApp templates and automation rules, ad spend (CRUD and CSV import), lead CSV import, reports, lead-to-customer conversion, and cleanup.

Run on a throwaway copy of the database, with the SMTP settings removed and the WhatsApp token blank, so no real email or WhatsApp message could be sent. Email send was checked only for the "not configured" rejection. Pass A: 102/102. Pass B: 102/102.

Bugs fixed:
- `POST /whatsapp/templates` returned 500: `created_at` and `updated_at` were never set, and both columns are NOT NULL. It also had no permission check. It now sets both timestamps and requires `crm.edit`, matching the automation-rule create.

Not exercised, by design: sending email and WhatsApp messages (they reach real recipients), saving SMTP settings, and firing automation rules on lead events.

Design note: there are two product catalogues, CRM products (`crm_products`) and inventory products (`products`). The lead screen uses the inventory list, so linking works, but a CRM product cannot be linked to a lead.

### Date picker hidden behind modals (2026-10-03)

Symptom: in New Task (and other modals), clicking "Select date…" showed nothing.

Cause: the modal overlay is at z-[9999], but the date picker's calendar was at z-[70], so the calendar was drawn behind the modal.

Fix: `frontend/src/components/shared/date-picker.tsx` now uses z-[10000], matching the searchable dropdown.

Verification: tsc and build pass, and the frontend container is rebuilt. Not yet clicked through in a browser.

### Public access via Cloudflare Tunnel (2026-10-05)

Hardened for public exposure, then exposed via `cloudflared`, keeping Postgres/Redis local-only (nginx is the only service a tunnel needs to reach; the DB is never exposed).

Changes:
- `APP_ENV` flipped to `production` in both `.env` and `docker-compose.yml` (the compose `environment:` block overrode `.env`, so both needed the change). This hides `/api/v1/docs` and `/api/v1/redoc`, lowers log verbosity, turns off SQL echo, and marks the refresh-token cookie `Secure`.
- Found and fixed a bug this flip would have exposed: `POST /auth/forgot-password` returned the OTP directly in the dev-mode response, but no code path ever emails it in production — "forgot password" would have silently done nothing. `backend/app/api/v1/endpoints/auth.py` now logs the OTP server-side (`logger.warning`) in production, so an admin can retrieve it from `docker compose logs backend` until real OTP email delivery is built.
- Brought the full stack back up — `nginx`, `frontend`, `celery_worker`, `celery_beat` had been stopped since earlier in this session (only backend/postgres/redis were running for QA testing).

Verification: full login → refresh round trip over a real public HTTPS Cloudflare Tunnel URL succeeded (access token issued, Secure cookie set, refresh accepted) using a disposable test user, which was deleted afterward. `/api/v1/docs` returns 404 through the tunnel.

Setup used for this session: `brew install cloudflared`, `cloudflared tunnel --url http://localhost:80` (quick/unnamed tunnel — a new random `*.trycloudflare.com` URL each time it restarts). Not yet set up: a named tunnel with a persistent URL/custom domain, or a login item / `brew services` daemon so it survives a reboot.

### Exception detail leak fixed (2026-10-05)

Found while confirming no internals leak to the public tunnel: `APP_DEBUG=true` in `.env` is a separate flag from `APP_ENV`, and flipping `APP_ENV` to production didn't touch it. With it true, any unhandled 500 returned the raw exception type and message to the client, e.g. the SQLAlchemy `ForeignKeyViolationError` seen during CRM testing — not source code, but table/column names and internal error detail. Flipped to `false` in `.env`. Verified: the same FK-violation trigger now returns `{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}` instead of the raw exception.

### Activities "Done" toggle: confirm before marking, instant revert, completed sink to bottom (2026-10-05)

`frontend/src/app/(app)/crm/activities/page.tsx` — three changes to the Done toggle, in both the list view and the calendar day-panel:

- Clicking Done on an open activity now opens a confirmation dialog ("Mark '<title>' as done?") before it commits — guards against an accidental tap.
- Clicking Done on an already-completed activity reverts it immediately, no confirmation — reverting stays a single click on purpose, since that's the undo path for an accidental mark.
- The list view now sorts completed activities to the bottom, open ones first, each group keeping its existing order.

Not done: a visible "Completed" section header/divider in the list — the shared `DataTable` component has no per-row styling or divider-row support, and extending it was out of scope here. The sort alone pushes completed items down, but there's no heading marking where that group starts.

Verification: `tsc --noEmit` and `npm run build` pass, frontend container rebuilt, `/crm/activities` returns 200 locally and through the tunnel. Not clicked through in a browser.

### Leads pipeline: fixed "No pipeline stages configured" bug, added clickable stage workflow (2026-10-05)

Root cause of "No pipeline stages configured yet.": `frontend/src/app/(app)/crm/leads/page.tsx` read `kanbanData?.data?.stages`, but `GET /crm/leads/kanban` returns the stage array directly as `data` (not `{stages: [...]}`). `.stages` on an array is always `undefined`, so the Kanban board — and drag-and-drop between its columns — never actually worked for any company, regardless of how many pipeline stages existed. Fixed by reading `kanbanData?.data` directly (3 call sites). The existing Kanban toggle view now also works as a side effect, not just the new feature below.

New: `PipelineStageStrip`, an attractive clickable chevron/arrow workflow bar above the List view's leads table. Each stage renders as an interlocking arrow segment (CSS `clip-path`), colored by the stage's own configured color (Won forced green, Lost forced red), showing the lead count and total value in that stage. Clicking a stage filters the list below to just that stage (wired through a new `stage_id` query param the backend already supported but the frontend never sent); clicking the active stage again, or "Clear filter," resets it.

Verification: `GET /crm/leads/kanban` for the real company now returns all 6 configured stages with correct per-stage lead counts and values; `GET /crm/leads?stage_id=...` matches the kanban aggregation's count exactly (checked against the Proposal stage: 1/1). `tsc --noEmit` and `npm run build` pass, frontend container rebuilt, `/crm/leads` returns 200.

FYI for the user: the "Won" stage's total value for this company shows as a very large number (₹3,00,00,00,000) — that's real stored data from an existing lead, not a display bug, but worth a sanity check since it's now visible at a glance where it wasn't before.

Not clicked through in a browser.

### Leads pipeline restyled as a flowchart (2026-10-05)

`PipelineStageStrip` in `frontend/src/app/(app)/crm/leads/page.tsx` rebuilt per request: sequential stages now flow top-to-bottom as connected rounded boxes with arrow connectors, branching into two pill-shaped Won/Lost outcomes at the end (SVG fork), matching the shapes/arrows in the reference flowchart image. Same click-to-filter behavior as before. Verified: tsc, build, container rebuild, `/crm/leads` 200.

### Lead Intelligence — Phase 1 audit only (2026-10-05)

User pasted a 26-step spec for a Lead Intelligence/scoring/duplicate-detection system. Per the spec's own Step 1 and the user's explicit choice, only the audit was done — no schema or code changes. Written to `docs/LEAD_INTELLIGENCE_AUDIT.md`.

Key findings: no IndiaMART integration or duplicate detection exists anywhere in the codebase; `CrmLead` has no source_lead_id/raw payload/structured requirement fields; the only precedent webhook (WhatsApp) has a single-tenant company-resolution shortcut not to repeat; phone/email normalization doesn't exist even in the one existing "dedup" (WhatsApp contacts, exact-string match only). Cross-checked against the existing `docs/PROLEEDS_FEATURE_AUDIT.md` (a separate, earlier initiative) — no overlap on scoring/duplicates, confirmed via full read. Also found, incidentally: the Leads list search box has never worked — the backend's `GET /crm/leads` has no `search` param, unlike Organizations/Persons/Products which do. Not fixed (audit-only scope); flagged for the user.

Proposed a 7-step phased plan in the audit doc, awaiting the user's go-ahead on which step to start.

### Lead Intelligence Phase 1 — real implementation (2026-10-05)

Built for real this time (last turn was audit-only). Migrations 043/044, additive. New `app/services/lead_intelligence.py`: normalization (phone/email, `NormalizedLeadInput`, manual + fixture-based IndiaMART adapters), duplicate detection (`find_duplicate`, exact/high_confidence/possible/none), repeat-contact detection (`find_repeat_contact`, using `crm_lead_stage_history` which — correction to last turn's audit — already existed), and the deterministic scoring engine (`score_lead`, 19 default rules seeded per company, company-configurable weights/thresholds).

Wired into `POST /crm/leads` (scores on create), plus new `POST /crm/leads/{id}/rescore`, `GET /crm/leads/check-duplicate`, `GET /crm/leads/{id}/repeat-contact`, and admin config endpoints (`/crm/scoring-rules`, `/crm/scoring-thresholds`, `/crm/service-areas`). Also fixed, since I was already in `list_leads`: the leads search box has never worked (backend had no `search` param) — found during last turn's audit, fixed here; added a `priority` filter alongside it.

Found and fixed during testing: a self-match bug in `find_duplicate` — scoring a lead already linked to a person always matched that person against themselves, showing every linked lead as an "exact" duplicate of itself. Fixed with an `exclude_person_id` param.

Frontend: `LeadIntelligenceCard` on the lead detail page (score, priority, expandable breakdown, duplicate/repeat-contact banners, rescore button). Priority badges (🔥 high / ⚠️ medium) on list rows and kanban cards. A "Lead Scoring" section in CRM Settings — per-rule weight/active editing, grouped by category, plus the two threshold inputs.

Verification: full functional test against real data (scoring, duplicate exclusion, repeat-contact, rescore, search, priority filter, service-area effect) — all correct after the self-match fix. 24-endpoint regression check against a fresh throwaway DB copy, 24/24 healthy (one false-positive in my own check script, not a real failure). `tsc --noEmit` and `npm run build` pass; both containers rebuilt.

Documentation: `docs/LEAD_SCORING.md` (full rule table, limitations stated plainly — GST only known post-conversion, keyword-heuristic signals not NLP, IndiaMART adapter unverified against a real payload).

Not built in this phase (explicitly out of scope, consistent with the spec's "deterministic first" and "no ML before real data" instructions): the full LeadSourceAdapter plugin registry beyond the two functions built, a dedicated service-areas settings UI (API-only), Phase 1 reporting (Step 25 — needs real scored-lead volume to mean anything), and anything from Phase 2 (assignment, follow-up automation, manager dashboard) — that's the next decision point.

### Lead Automation Phase 2 (2026-10-05)

Built on the real Phase 1 engine. Migration 045 (assignment rules/pool/round-robin state, response-time + escalation fields on leads, response-target/escalation config on companies).

Found before building anything: `_assign_lead` already notified, created a first-contact task, and fired WhatsApp on manual assignment; `flag_missed_followups` (hourly Celery) already auto-creates tasks + notifies + fires WhatsApp for lapsed scheduled follow-ups, idempotently. Both reused/extended rather than duplicated — new `app/services/lead_assignment.py` (rule-based + round-robin) calls the same `_assign_lead` auto-assignment goes through, just with a priority-aware task due date.

New: `POST /crm/leads` auto-assigns (rule-based first, round-robin fallback) when nobody picks an assignee by hand; `response_target_at` set from company-configurable priority targets; `first_contacted_at` tracked separately from the pre-existing `last_contacted_at`; new Celery task `escalate_uncontacted_high_priority_leads` (every 30 min, two-stage idempotent escalation — employee then company owners); `GET /crm/reports/response-time`; admin endpoints for assignment rules/pool/response-targets.

Frontend: new `/crm/my-work` page (5 live sections, employee-scoped); CRM Settings → Lead Assignment section (rules, round-robin pool, response targets); a company-wide "high-priority uncontacted" banner on the CRM Dashboard linking to My Work.

Bug found and fixed during verification: `ResponseTargetsOut` (and `ScoringThresholdsOut`, same latent issue, unused code path so never triggered) missing `model_config = {"from_attributes": True}` — 500 on `GET/PUT /crm/response-targets`. Fixed, reverified with a full round trip.

Verified: full chain (create → score → auto-assign rule-then-round-robin → task → response target) against real data; escalation task run directly and confirmed idempotent; 24-endpoint regression sweep, 24/24 healthy; tsc/build clean; both containers rebuilt.

Documented in `docs/LEAD_AUTOMATION.md`, including what was deliberately deferred: catalogue/quotation/sample auto-follow-up tasks, structured outcome picker, employee workload view, platform/ad-spend quality reporting, unified activity timeline, pre-due reminders, dedicated manager dashboard page.

### Predictive Lead Scoring Phase 3 — data audit, no model built (2026-10-05)

Per the spec's own repeated instruction ("do not implement premature AI... if there is not enough data: BUILD THE DATA FOUNDATION... never fabricate accuracy"), ran the real data-readiness audit first, against the live database, before building anything.

Result: **9 total leads** for the real company, 1 won, 1 lost, spanning 29 days. `sales_order_id` unset on all 9 (conversion can't be traced to orders yet). 0 leads scored (score_lead only runs on new leads, no backfill). 0 stage-history rows. Nowhere close to viable for any model — documented with full numbers in `docs/PREDICTIVE_SCORING_DATA_AUDIT.md`.

No model, feature store, training pipeline, or model registry was built — would be fabricating accuracy on 2 labeled examples. Built instead, per the audit's own recommendation and spec Phase 30 ("data sufficiency gates"): migration 046 (`companies.predictive_scoring_min_leads`=200, `predictive_scoring_min_outcomes_per_class`=30, both configurable), `GET /crm/predictive-scoring/readiness` (live, honest counts vs. thresholds, never fabricates a score), and a small status card in CRM Settings explicitly labeled "Not Available Yet."

Verified live: endpoint returns `ready: false` with the real 9/200, 1/30, 1/30 numbers. Settings page loads the card correctly. `tsc`/`build` clean, both containers rebuilt.

`docs/PREDICTIVE_SCORING_ARCHITECTURE.md` documents the gate design and the planned future architecture (prediction-point-A-only feature extraction, model versioning, rule-score-stays-permanent, human override separate from model). The spec's other two requested docs (MODEL, OPERATIONS) were deliberately not written — there's no model or training process yet to document; writing them now would be fabricating documentation of something that doesn't exist, the same problem the spec warns against in a different form.

Revisit via the readiness endpoint, not on a calendar.

### Lead-to-order link gap fixed + demo data added (2026-10-05)

Per the user's instruction after the Phase 3 audit flagged this: `sales_order_id` was correctly set by `convert_lead_to_sales_order` but never exposed via `GET /crm/leads`/`GET /crm/leads/{id}` — a real, separate bug found while verifying. Added to `LeadOut`/`LeadListOut`, populated in both output helpers. Created 2 new `[DEMO]`-labeled leads to verify end-to-end: one converted through the real endpoint (confirmed `sales_order_id` now appears in the API response), one marked lost for symmetry. Updated audit numbers: 11 leads (was 9), 2 won, 2 lost, 1 genuinely order-linked (was 0) — readiness gate still correctly reports `ready: false` (11/200, 2/30, 2/30); two demo leads don't and shouldn't change that conclusion. `docs/PREDICTIVE_SCORING_DATA_AUDIT.md` updated with this note.

### Sales Pipeline redesigned as an SVG journey visualization (2026-10-05)

Replaced `PipelineStageStrip` (the vertical flowchart built earlier this session) entirely, per a detailed 36-section design brief. New component: `frontend/src/components/crm/sales-pipeline-journey.tsx` (`SalesPipelineJourney`).

- **Layout**: a pure function of stage count (`layoutDesktop`/`layoutMobile`) — linear stages ascend left-to-right (desktop) or stack top-to-bottom (mobile, <768px), terminal stages (won/lost, or however many `is_won`/`is_lost` flags exist) fan out from the last linear stage. Adapts to 1 stage or 10+ with no hardcoding — tested against the real pipeline (4 linear + 2 terminal) and manually traced for 1/3/7-stage cases.
- **Path**: one SVG `<path>` with smooth S-curve bezier segments (not per-segment DOM elements), indigo→blue→violet gradient, soft glow filter, stroke-draw-in animation on mount.
- **Nodes**: real `<button>` elements overlaid on the SVG (keyboard-focusable, `aria-label` with stage/count/value/action, visible focus ring) — not raw SVG click targets. Won green, Lost muted red, selected/hover/pulse states.
- **Tooltip**: real data only (count, pipeline value, % of pipeline volume) — no fabricated conversion-rate numbers.
- **Currency**: new `frontend/src/lib/format.ts` (`formatIndianCompact`/`formatIndianFull`) — ₹10.40 L / ₹300.00 Cr / ₹0, never raw NUMERIC output. Verified against real data (New ₹10.40L, Qualified ₹6.05L, Won ₹300.00Cr).
- **States**: loading skeleton, error with Retry, empty ("No active opportunities"), all distinct from the live view (never 0/₹0 masquerading as real data).
- **Pipeline selector**: added — a native `<select>` of real `GET /crm/pipelines` records, wired to `GET /crm/leads/kanban?pipeline_id=`, verified working against the real API (hidden when only one pipeline exists, since the current company has exactly one).
- **Reduced motion**: `prefers-reduced-motion` media query disables all animation, verified in the component's own stylesheet.
- **Click-to-filter preserved exactly** — same `onSelect`/`stageFilter` contract as before, filters the list below via the existing `stage_id` query param.
- **No backend changes for the redesign itself** — `column_value`, counts, colors, `is_won`/`is_lost` were already backend-computed; the component only formats and visualizes.

Verification: tsc/build clean, frontend container rebuilt, `/crm/leads` renders server-side with no error markers, kanban endpoint re-tested directly with an explicit `pipeline_id` param. Not clicked through in a browser — animation, hover tooltip positioning, and the mobile breakpoint specifically need a visual check.
