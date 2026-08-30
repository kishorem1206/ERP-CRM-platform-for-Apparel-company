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
