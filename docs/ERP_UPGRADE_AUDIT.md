# ERP Upgrade — Phase 0 Audit
**Date:** 2026-08-29
**Status:** Complete

---

## A. Tech Stack Summary

| Layer | Technology |
|---|---|
| Frontend | Next.js 14.2.14, TypeScript 5.6, Tailwind CSS 3.4, TanStack Query v5, Axios |
| Backend | FastAPI 0.115, Python 3.11+, SQLAlchemy 2.0 async, Uvicorn |
| Database | PostgreSQL 16 (extensions: uuid-ossp, pg_trgm) |
| ORM / Migrations | SQLAlchemy 2.0 mapped_column style + Alembic (2 migrations applied) |
| Auth | JWT (python-jose) + bcrypt + pyotp (TOTP/2FA) + Redis |
| AI | OpenAI-compatible SDK + LangGraph 0.2 + LangChain-core |
| Queue/Cache | Celery 5.4 + Redis |
| Storage | Local filesystem or AWS S3 (boto3) |
| Infra | Docker Compose (dev + prod), Nginx, GitHub Actions CI |

---

## B. Database Tables — Complete List

### System / Infrastructure
| Table | Description |
|---|---|
| `companies` | Single company tenant; GST, PAN, currency, fabric_variance_pct, negative_stock_allowed |
| `users` | Users per company; 2FA, lockout, is_owner |
| `roles` | RBAC roles per company; is_system flag |
| `permissions` | Global permission codes (e.g. `inventory.view`) |
| `role_permissions` | Junction: role_id + permission_id |
| `user_roles` | Junction: user_id + role_id |
| `refresh_tokens` | JWT refresh tokens; revoked_at, expires_at |
| `audit_logs` | Entity audit trail: entity_type, action, old/new JSONB |
| `document_sequences` | Concurrency-safe auto-numbering per document_type |
| `notifications` | Push notifications per user |
| `agent_conversations` | AI chat sessions |
| `agent_messages` | AI message history with tool_calls/results JSONB |

### Master Data
| Table | Description |
|---|---|
| `units` | Units of measure (weight/length/piece/volume) |
| `categories` / `sub_categories` | Product category hierarchy |
| `brands` | Brand master |
| `sizes` | Garment size master (sort_order) |
| `colours` | Colour master (hex_code) |
| `hsn_codes` | GST HSN master with gst_rate, cess_rate |
| `warehouses` | Warehouses per company (code unique, is_active) |
| `warehouse_locations` | Sub-locations within warehouses |

### Products
| Table | Description |
|---|---|
| `products` | product_type enum (finished_good/yarn/fabric/trim/packing/raw_material); full apparel attributes (gsm, construction, fabric_type, composition, etc.) |
| `product_variants` | SKU variants (colour+size); COALESCE NULL-safe unique index |
| `product_images` | Product images (is_primary, sort_order) |
| `price_lists` | Named price lists per company |
| `price_list_items` | Prices per product/variant with quantity bands |

### CRM / Customers
| Table | Description |
|---|---|
| `customers` | Full B2B customer master (migration 002 extended: mobile, whatsapp_no, landline_no, email, contact_person_name, nature_of_business_id, contact_type, payable/receivable_opening_balance, discount_percent, tds_percent, enable_tcs, due_days, accounts_manager_id, agent_id, agent_commission_percent, customer_rating, other_details, remarks, customer_portal_enabled) |
| `customer_addresses` | Billing/shipping addresses |
| `customer_contacts` | Contact persons (created_at, updated_at added migration 002) |
| `customer_details` | Repeatable key-value rows per customer (migration 002) |
| `leads` | Sales leads: status (new/contacted/qualified/converted/lost), source, assigned_to |
| `nature_of_business` | Master: Manufacturer/Trader/Retailer/Exporter/etc. (migration 002) |

### Vendors
| Table | Description |
|---|---|
| `vendors` | Vendor master; vendor_type (supplier/job_worker/transporter) |
| `vendor_contacts` | Vendor contact persons |
| `vendor_bank_details` | Bank details (IFSC, account_number, is_primary) |

### Materials (Textile-Specific) ⚠️ SCHEMA DRIFT — see Section G
| Table | Description |
|---|---|
| `inventory_lots` | Yarn/Fabric/Trim/FG lots; yarn_count, ply, mill, spinning_type, treatment, fibre_type, blend_composition, construction, gsm, diameter_inches, colour, finish; **bags, kg_per_bag, trim_type, trim_unit, split_by_colour, split_by_dia** — IN ORM ONLY, NOT IN MIGRATIONS |
| `material_composition_items` | Fibre composition rows (fibre_name, percentage) — **IN ORM ONLY, NOT IN MIGRATIONS** |
| `fabric_variants` | Colour+dia sub-rows per fabric lot — **IN ORM ONLY, NOT IN MIGRATIONS** |
| `trim_variants` | Colour sub-rows per trim lot — **IN ORM ONLY, NOT IN MIGRATIONS** |
| `fabric_runs` | Fabric production runs (input lot → output lot, wastage, machine, status) |
| `inventory_transactions` | All stock movements: direction (+1/-1), material_type, lot_id, reference_type/id, unit_cost, total_cost |
| `inventory_balance` | Materialized view: current stock per product/variant/warehouse/material_type |

### Purchase
| Table | Description |
|---|---|
| `purchase_orders` | POs: draft→approved→partial→received→cancelled; GST breakdown |
| `purchase_order_items` | Line items: ordered_qty, received_qty, discount, GST |
| `purchase_entries` | GRNs linked to PO (optional); invoice_number/date |
| `purchase_entry_items` | GRN items: accepted/rejected qty, quality_status, inv_transaction_id |

### Sales
| Table | Description |
|---|---|
| `quotations` | GST breakdown; status lifecycle; billing_address_id |
| `quotation_items` | Line items with CGST/SGST/IGST |
| `sales_orders` | Status (confirmed/processing/partial/completed/cancelled) |
| `sales_order_items` | SO line items with delivered_qty tracking |
| `deliveries` | Delivery notes; transporter, lr_number, dispatched_at |
| `delivery_items` | Delivery items with lot_id and inv_transaction_id |
| `invoices` | Tax invoices; paid_amount, balance_amount, cess_amount |

### Production
| Table | Description |
|---|---|
| `styles` | Garment styles (garment_type, gender, season) |
| `production_lots` | Lot lifecycle (10+ statuses); style_id, customer_id, sales_order_id, planned_qty, actual_qty |
| `production_lot_sizes` | Qty per size (cut/sewn/finished) |
| `production_stages` | Cutting/Making/Finishing/QC/Packing/Dispatch; job worker, rate/pc |
| `production_stage_entries` | Daily entries: pieces_in/out, rejected, operator, machine |
| `material_issues` | Material Issue Slips: materials from warehouse to production lot |
| `material_issue_items` | MIS items: product, lot, planned/issued qty, inv_transaction_id |
| `production_outputs` | FG received into warehouse; unit_cost, inv_transaction_id |

### Finance
| Table | Description |
|---|---|
| `receipts` / `payments` | Old schema (stale in schema.sql) |
| `Payment` / `PaymentAllocation` | Active ORM: customer receipts with invoice allocation |
| `VendorPayment` / `VendorPaymentAllocation` | Active ORM: vendor payments |
| `CreditNote` / `DebitNote` | Credit and debit notes |
| `expense_categories` / `expenses` | Expense tracking |

### Files
| Table | Description |
|---|---|
| `file_attachments` | Polymorphic: entity_type + entity_id, file_url |

---

## C. API Endpoints — Complete List

**Base:** `/api/v1/`

| Module | Endpoints |
|---|---|
| Auth | POST /auth/login, /refresh, /logout, /forgot-password, /reset-password; GET /auth/me; POST /auth/2fa/setup, /verify, /disable |
| Agents | POST /agents/chat; GET /agents/conversations, /conversations/{id} |
| Attachments | POST /attachments/upload; GET /attachments/{entity_type}/{entity_id}; DELETE /attachments/{id} |
| Products | GET/POST /products; GET/PATCH /products/{id}; POST /products/{id}/variants |
| Master | GET /master/categories, /sizes, /colours, /units, /warehouses, /hsn |
| Purchase | GET/POST /purchase/vendors; GET/PATCH /purchase/vendors/{id}; GET/POST /purchase/orders; GET/PATCH /purchase/orders/{id}; POST /purchase/orders/{id}/approve, /cancel; GET/POST /purchase/entries; GET /purchase/entries/{id} |
| Sales | GET /sales/nature-of-business; GET/POST /sales/customers; GET/PATCH /sales/customers/{id}; full quotation→SO→delivery→invoice CRUD + status transitions |
| Production | GET/POST /production/styles; GET/POST /production/lots; GET/PATCH /production/lots/{id}; POST /production/lots/{id}/status, /stages; POST /production/stages/{id}/entries; GET/POST /production/mis, /outputs |
| Finance | GET/POST /finance/payments, /vendor-payments, /credit-notes, /debit-notes; GET /finance/ledger/customer/{id}, /ledger/vendor/{id}, /gst/output, /gst/input |
| Inventory | POST /inventory/stock-in, /stock-out, /transfer, /adjust; GET /inventory/transactions, /balance |
| **Materials** | POST /materials/yarn, /fabric, /trims, /fabric-runs; GET /materials/lots, /lots/{id}, /fabric-runs |
| Reports | GET /reports/sales-summary, /purchase-summary, /production-efficiency, /gst-summary, /stock-ageing |
| Admin | Full CRUD for /admin/users, /roles, /permissions; PUT /admin/roles/{id}/permissions; GET/PUT /admin/company |
| Notifications | GET /notifications; POST /notifications/{id}/read, /read-all |

---

## D. Frontend Pages — Complete List

### Auth
`/login`, `/forgot-password`, `/reset-password`

### App (authenticated)
| Route | What it shows |
|---|---|
| `/dashboard` | 6 KPI cards, revenue vs purchase chart, production status donut, top customers bar chart |
| `/crm` | CRM overview |
| `/crm/customers` | Customer list (code, legal_name, trade_name, mobile, email, GSTIN, type, status) |
| `/crm/customers/new` | Full tabbed Add Customer form (Company/Addresses/Contacts/Accounting/Team/Other) |
| `/crm/customers/[id]` | Full tabbed Edit Customer form |
| `/sales` | Sales overview |
| `/sales/quotations` | Quotation list |
| `/sales/orders` | Sales orders list |
| `/sales/deliveries` | Deliveries list |
| `/sales/invoices` | Invoices list |
| `/purchase` | Purchase overview |
| `/purchase/vendors` | Vendor list |
| `/purchase/orders` | PO list |
| `/purchase/grn` | GRN list |
| `/inventory` | Inventory overview |
| `/inventory/products` | Product catalog |
| `/inventory/stock-in`, `/stock-out`, `/transfer`, `/adjust` | Manual stock operations |
| `/inventory/transactions` | Transaction log |
| `/inventory/balance` | Current stock balance |
| `/production` | Production overview |
| `/production/lots` | Production lots list with inline NewLotModal |
| `/production/mis` | Material Issue Slips |
| `/production/outputs` | Production outputs |
| `/finance` | Finance overview |
| `/finance/payments`, `/vendor-payments`, `/credit-notes`, `/debit-notes`, `/gst` | Finance screens |
| `/reports/sales`, `/purchases`, `/production`, `/gst`, `/stock-ageing` | Report screens |
| `/admin/users`, `/roles`, `/roles/[id]`, `/company` | Admin screens |
| `/ai-assistant` | AI chat interface |
| `/settings/security` | 2FA setup |

### Global UI Components
- **CreateMenu** (Topbar) — Quick Create panel with 5 actions: New Lot, New Fabric Run, Add Yarn, Add Fabric, Add Trims
- **NewLotModal**, **NewFabricRunModal**, **AddYarnModal**, **AddFabricModal**, **AddTrimsModal**
- **DataTable**, **KpiCard**, **StatusBadge**, **ModalPortal**

---

## E. Working Features

| Feature | Status |
|---|---|
| JWT + Refresh token auth | ✅ Working |
| TOTP 2FA | ✅ Working |
| Account lockout | ✅ Working |
| Password reset via OTP | ✅ Working |
| RBAC (roles + permissions) | ✅ Working |
| Dashboard KPIs and charts | ✅ Working |
| B2B Customer master | ✅ Working (extended migration 002) |
| Customer addresses/contacts | ✅ Working |
| Leads table | ⚠️ Backend only, no frontend page |
| Quotation → SO → Delivery → Invoice | ✅ Working |
| GST calculation (intrastate/interstate) | ✅ Working |
| Customer payment + invoice allocation | ✅ Working |
| Credit/debit notes | ✅ Working |
| Vendor master | ✅ Working |
| Purchase Order → GRN flow | ✅ Working |
| Vendor payment | ✅ Working |
| Inventory transactions (stock-in/out/transfer/adjust) | ✅ Working |
| Materialized balance view | ✅ Working (needs Celery refresh) |
| Style master | ✅ Working |
| Production lots (10+ status lifecycle) | ✅ Working |
| Production stages + daily entries | ✅ Working |
| Material Issue Slips (MIS) | ✅ Working |
| Production outputs (FG to warehouse) | ✅ Working |
| **Add Yarn** (Quick Create) | ✅ Working (SCHEMA DRIFT — see risk) |
| **Add Fabric** (Quick Create) | ✅ Working (SCHEMA DRIFT — see risk) |
| **Add Trims** (Quick Create) | ✅ Working (SCHEMA DRIFT — see risk) |
| **New Lot** (Quick Create) | ✅ Working |
| **New Fabric Run** (Quick Create) | ✅ Working |
| Fabric runs (input→output→wastage) | ✅ Working |
| Finance reports (GST register, ledgers) | ✅ Working |
| Admin user/role management | ✅ Working |
| AI assistant (intent routing + DB tools) | ✅ Working (tool coverage gaps — see risks) |
| File attachments (polymorphic) | ✅ Working |
| Notifications | ✅ Working |
| Document sequence auto-numbering | ✅ Working (needs seed data per doc type) |

---

## F. Gap Analysis

### Target Workflows vs Existing System

| Target Workflow | Gap Status | Detail |
|---|---|---|
| New Lot | **NO GAP — Already implemented** | `POST /production/lots`, `NewLotModal.tsx`, full lot lifecycle |
| New Fabric Run | **NO GAP — Already implemented** | `POST /materials/fabric-runs`, `NewFabricRunModal.tsx` |
| Add Yarn | **NO GAP — Already implemented** | `POST /materials/yarn`, `AddYarnModal.tsx`, full fields |
| Add Fabric | **NO GAP — Already implemented** | `POST /materials/fabric`, `AddFabricModal.tsx`, full fields incl. split_by_colour/dia |
| Add Trims | **NO GAP — Already implemented** | `POST /materials/trims`, `AddTrimsModal.tsx`, full fields |

**All 5 target workflows are already coded end-to-end.** The upgrade plan from the prompt assumes they don't exist — they do. The real work is elsewhere.

### Actual Gaps Found

| Gap | Priority | Detail |
|---|---|---|
| Schema drift: 4 tables + ~8 columns in ORM but not in migrations | **CRITICAL** | AddYarn/Fabric/Trims will fail on a fresh DB install |
| Inventory booking not wired in Add Material modals | **HIGH** | Lots created without inventory transactions; stock balance not updated |
| No `/crm/leads` frontend page | Medium | Leads table and model exist; no UI |
| AI agents for finance/purchase use general LLM (no DB tools) | Medium | Answers from memory, not live data |
| Material lot detail / traceability page missing | Medium | No `/inventory/lots/[id]` UI |
| MIS (Material Issue Slips) UI may be incomplete | Medium | Backend works; frontend needs verification |
| Lot → Buyer/Order traceability UI | Low | Data model supports it; no dedicated view |
| document_sequences not seeded for material types | Low | Auto-numbering falls back to COUNT-based |

---

## G. Tables That Need Migration (Schema Drift — CRITICAL)

Create **migration 003** to add:

### New Tables
```sql
CREATE TABLE material_composition_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
    fibre_name VARCHAR(100) NOT NULL,
    percentage NUMERIC(5,2) NOT NULL,
    sort_order SMALLINT DEFAULT 0
);

CREATE TABLE fabric_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
    colour VARCHAR(100),
    diameter_inches NUMERIC(6,2),
    quantity NUMERIC(12,3) DEFAULT 0,
    unit_id UUID REFERENCES units(id)
);

CREATE TABLE trim_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lot_id UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE CASCADE,
    colour VARCHAR(100),
    quantity NUMERIC(12,3) DEFAULT 0
);
```

### New Columns on `inventory_lots`
```sql
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS bags NUMERIC(10,2);
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS kg_per_bag NUMERIC(10,3);
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS trim_type VARCHAR(50);
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS trim_unit VARCHAR(30);
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS split_by_colour BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS split_by_dia BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## H. New Tables Required (Beyond Drift Fix)

For full textile ERP traceability (future phases):

| Table | Purpose |
|---|---|
| `lot_material_links` | Explicit yarn/fabric lot → production lot traceability (currently via MIS only) |
| `yarn_dyeing_jobs` | Track greige → dyed yarn with dye lot, colour, process |
| `fabric_dyeing_jobs` | Track greige → dyed fabric with dye lot, colour, process |

---

## I. Files That Will Need Modification

### Immediate (Phase 1 — Schema Drift Fix)
- **Create** `backend/alembic/versions/003_materials_tables.py`
- **Update** `db/schema.sql` (documentation sync)

### Near-term (Phase 2–5)
- `backend/app/api/v1/endpoints/materials.py` — add PATCH endpoints, lot detail GET with compositions/variants
- `backend/app/schemas/materials.py` — add Update schemas
- `backend/app/services/materials.py` — add update methods, close_fabric_run
- `frontend/src/components/create/AddYarnModal.tsx` — add optional warehouse/product/unit for inventory booking
- `frontend/src/components/create/AddFabricModal.tsx` — same
- `frontend/src/components/create/AddTrimsModal.tsx` — same
- **Create** `frontend/src/app/(app)/inventory/lots/page.tsx` — material lot browser
- **Create** `frontend/src/app/(app)/inventory/lots/[id]/page.tsx` — lot detail + traceability
- **Create** `frontend/src/app/(app)/crm/leads/page.tsx` — leads list

### Longer-term (Phase 6+)
- `backend/app/agents/specialist/finance_agent.py` — wire real DB tools
- `backend/app/agents/specialist/purchase_agent.py` — wire real DB tools
- Production lot detail page enhancements
- Buyer/order to lot traceability views

---

## J. Critical Risks

| # | Risk | Severity | Action |
|---|---|---|---|
| 1 | **Schema drift** — `material_composition_items`, `fabric_variants`, `trim_variants` + ~8 columns exist ONLY in ORM, NOT in migrations. Fresh DB install will break Add Yarn/Fabric/Trims | **CRITICAL** | Create migration 003 immediately |
| 2 | **Inventory not booked on material receipt** — Add Yarn/Fabric/Trims creates a lot record but no inventory transaction unless separately triggered; stock balance won't reflect receipts | **HIGH** | Wire inventory booking into material modals |
| 3 | **Materialized view not refreshing** — `inventory_balance` requires `REFRESH MATERIALIZED VIEW`; Celery task existence unconfirmed | **HIGH** | Verify Celery tasks; ensure refresh fires after every transaction |
| 4 | **`document_sequences` not seeded** — Material auto-numbering falls back to COUNT if no sequence row exists for yarn/fabric/trim/fabric_run types | Medium | Seed document_sequences on company setup |
| 5 | **AI finance/purchase agents** — use general LLM with no live DB tools; will hallucinate financial data | Medium | Add DB tools to finance and purchase agents |
| 6 | **Finance schema mismatch** — `schema.sql` shows old receipts/payments tables; active ORM uses newer Payment/CreditNote models | Medium | Update schema.sql documentation |
| 7 | **No Leads frontend** — leads table exists but `/crm/leads` page does not | Low | Create leads page in CRM phase |

---

## K. What Must NOT Be Changed

1. **`inventory_transactions`** structure — direction, lot_id, material_type are final; materialized view depends on them
2. **`inventory_balance` materialized view** — COALESCE sentinel for NULL variant_id; do not alter structure
3. **JWT payload fields** — `sub` (user_id), `company_id`, `permissions` used by all API deps
4. **`document_sequences`** table and FOR UPDATE pattern — concurrency-safe; do not simplify
5. **`company_id` tenant isolation** — every query scoped by it; must be preserved on every new endpoint
6. **`production_lots` status values** — 10+ statuses used across UI and reports; renaming breaks data
7. **COALESCE sentinel UUID** on variant unique indexes — `product_variants` and `inventory_balance` both use this pattern
8. **Existing modals/workflows** — NewLotModal, NewFabricRunModal, AddYarnModal, AddFabricModal, AddTrimsModal are working; don't replace, only extend

---

## L. Recommended Phase 1 Starting Point

**The all-5 target workflows are already implemented.** Phase 1 should focus on making them reliable:

1. **Fix schema drift** — create migration 003 (critical, ~2 hours)
2. **Wire inventory booking** into the material modals (2–3 days)
3. **Verify and fix Celery materialized view refresh** (1 day)
4. **Seed document_sequences** for material types (2 hours)
5. **Create material lot browser + detail page** (3–5 days)
6. **Create leads frontend page** (1 day)

After these, proceed with AI tool coverage, buyer/lot traceability, and the remaining ERP integration phases.

---

*Audit complete. Saved: 2026-08-29. Next: Phase 1 confirmation required.*
