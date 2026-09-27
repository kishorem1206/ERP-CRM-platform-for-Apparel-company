# Apparel Manufacturing CRM/ERP — Product Document

**Version:** 1.0  
**Stack:** FastAPI · PostgreSQL · LangGraph · Next.js · Docker  
**Domain:** Apparel manufacturing — yarn → fabric → garment → delivery

---

## 1. Product Overview

A production-grade enterprise CRM/ERP built for apparel manufacturers. It replaces spreadsheets and disconnected tools with a single system covering raw material procurement, fabric/yarn inventory, production lot tracking, garment costing, GST-compliant sales/purchase, financial management, and an AI assistant that can read, suggest, and execute ERP actions through natural language.

### Who uses it

| Role | Primary modules |
|------|----------------|
| Owner / MD | Dashboard, Finance, Reports, AI Assistant |
| Production Manager | Production lots, Material issue, Stage tracking |
| Purchase Manager | Purchase Orders, Vendor management |
| Sales / CRM | Quotations, Sales Orders, Customer 360 |
| Store / Warehouse | Inventory, Stock movements |
| Accountant | Finance, GST, Outstanding |
| Admin | Users, Roles, Company settings |

---

## 2. Module Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        MASTER DATA                              │
│  Customer · Product/Variants · Vendor · Employee · Warehouse    │
│  Size · Colour · HSN · Tax/GST · Price List · Unit Master       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐
   │   CRM   │    │INVENTORY │    │ PURCHASE │
   │  Sales  │    │  Ledger  │    │    PO    │
   └────┬────┘    └────┬─────┘    └────┬─────┘
        │              │               │
        └──────────────┼───────────────┘
                       │
                  ┌────▼─────┐
                  │PRODUCTION│
                  │  Lots    │
                  │  Stages  │
                  │  WIP     │
                  └────┬─────┘
                       │
               ┌───────┼───────┐
               ▼       ▼       ▼
          COSTING   FINANCE   GST
          Engine    Module    Engine
               │       │       │
               └───────┼───────┘
                       │
                  ┌────▼─────┐
                  │ REPORTS  │
                  │Analytics │
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │AI AGENTS │
                  │LangGraph │
                  └──────────┘
```

### Module responsibilities

| Module | Responsibility |
|--------|---------------|
| Master Data | All reference/configuration entities. Foundation for every transaction. |
| CRM | Leads, customers, contacts, activities, opportunities, follow-ups. |
| Sales | Quotation → Sales Order → Delivery → Invoice → Payment. |
| Purchase | Purchase Requisition → PO → Goods Receipt → Vendor Invoice → Payment. |
| Inventory | Ledger-based stock for Yarn / Fabric / Trims / WIP / Finished Goods. |
| Production | Production lots, fabric runs, stage tracking, material consumption. |
| Costing | Product cost sheets, production cost actuals vs. planned. |
| Finance | Receipts, Payments, Expenses, Ledgers, Aging. |
| GST | CGST/SGST/IGST determination, HSN mapping, tax reporting. |
| Reports | Parameterised reports with CSV/Excel/PDF export. |
| Administration | Users, Roles, Permissions, Company settings, Audit viewer. |
| AI Agents | LangGraph orchestrator + specialist agents over all modules. |

---

## 3. Database Architecture

### 3.1 Core conventions

- All primary keys: UUID v4
- Timestamps: `created_at`, `updated_at` (UTC, `timestamptz`)
- Soft deletes: `deleted_at` (null = active)
- Audit columns: `created_by`, `updated_by` (user UUID FK)
- Money: `NUMERIC(15, 2)` — never `FLOAT`
- Quantities: `NUMERIC(15, 4)` to handle fractional units (kg, metres)
- All tables inherit from `BaseModel` (SQLAlchemy declarative base)

### 3.2 Inventory ledger (critical design)

Inventory is **never a mutable stock field**. Every change creates an immutable ledger entry.

```
inventory_transactions
  id              UUID PK
  transaction_type  ENUM (stock_in, stock_out, transfer_in, transfer_out,
                          adjustment, opening_balance, production_issue,
                          production_return, production_output,
                          sales_dispatch, purchase_receipt,
                          sales_return, purchase_return, damage, scrap)
  reference_type  VARCHAR   -- 'purchase_entry', 'sales_order', 'production_lot', etc.
  reference_id    UUID
  material_type   ENUM (yarn, fabric, trim, wip, finished_good, packing)
  product_id      UUID FK → products
  variant_id      UUID FK → product_variants (nullable)
  warehouse_id    UUID FK → warehouses
  location_id     UUID FK → warehouse_locations (nullable)
  lot_id          UUID FK → inventory_lots (nullable)  -- batch traceability
  quantity        NUMERIC(15,4)
  unit_id         UUID FK → units
  unit_cost       NUMERIC(15,2)
  total_cost      NUMERIC(15,2)
  direction       SMALLINT  -- +1 (in) or -1 (out)
  transaction_date DATE
  notes           TEXT
  created_at      TIMESTAMPTZ
  created_by      UUID FK → users
```

Current stock is derived:
```sql
SELECT product_id, variant_id, warehouse_id, SUM(quantity * direction) AS current_qty
FROM inventory_transactions
GROUP BY product_id, variant_id, warehouse_id;
```

A materialised view `inventory_balance` refreshes this for performance.

### 3.3 Key entity groups

**Master Data**
```
companies, users, roles, permissions, role_permissions, user_roles
customers, customer_addresses, customer_contacts
vendors, vendor_contacts, vendor_bank_details
employees
products, product_variants, product_images
sizes, colours, categories, sub_categories, brands
units, warehouses, warehouse_locations
hsn_codes, tax_rates, price_lists, price_list_items
```

**Inventory**
```
inventory_transactions  -- the ledger (immutable)
inventory_lots          -- batch/lot master (yarn lot, fabric lot, trim lot)
inventory_balance       -- materialised view
```

**Purchase**
```
purchase_requisitions, purchase_requisition_items
purchase_orders, purchase_order_items
purchase_entries, purchase_entry_items  -- goods receipt
purchase_returns, purchase_return_items
vendor_invoices
```

**Sales / CRM**
```
leads, lead_activities
opportunities
quotations, quotation_items
sales_orders, sales_order_items
deliveries, delivery_items
invoices, invoice_items
sales_returns, sales_return_items
customer_payments
```

**Production**
```
styles                    -- Style Master: the production blueprint (see §11.1)
style_sizes, style_colours              -- applicable size chart / colour variants
style_yarns, style_fabrics              -- material requirements, referencing materials masters
style_processes, style_sub_processes    -- configurable process workflow, per-process tolerance/units/rates
style_trims, style_packing_materials    -- trim & packing-material planning
production_lots           -- garment production run (snapshots a Style at creation time)
production_lot_sizes      -- size-wise qty breakdown
production_stages         -- snapshotted from style_processes at LOT creation (tolerance/units/rates frozen)
production_stage_entries  -- daily log entries per stage
fabric_runs               -- yarn → grey → dyed → finished fabric
fabric_run_stages
material_issues           -- stock → production
material_returns          -- production → stock
production_outputs        -- production → finished goods
```

**Finance**
```
receipts, receipt_items
payments, payment_items
expenses, expense_categories
customer_ledger_entries
vendor_ledger_entries
```

**System**
```
audit_logs
document_sequences        -- auto-numbering per document type
company_settings
notification_logs
background_jobs
```

### 3.4 Audit log

```
audit_logs
  id              UUID PK
  entity_type     VARCHAR  -- 'quotation', 'sales_order', etc.
  entity_id       UUID
  action          ENUM (create, update, delete, status_change, approve, cancel)
  old_value       JSONB
  new_value       JSONB
  changed_fields  TEXT[]
  user_id         UUID FK → users
  ip_address      INET
  request_id      UUID
  created_at      TIMESTAMPTZ
```

### 3.5 Document numbering

```
document_sequences
  document_type  VARCHAR PK  -- 'quotation', 'sales_order', 'invoice', etc.
  prefix         VARCHAR      -- 'QT', 'SO', 'INV'
  separator      VARCHAR      -- '/'
  year_format    VARCHAR      -- 'YY' or 'YYYY' or ''
  next_number    INTEGER
  padding        INTEGER      -- zero-pad width (e.g. 4 → 0001)
```

Generated: `QT/26/0042`, `SO/2026/0017`, `INV/0001`

---

## 4. API Architecture

### 4.1 Versioning

All routes under `/api/v1/`. Future breaking changes introduce `/api/v2/`.

### 4.2 Response envelope

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "per_page": 25, "total": 142 }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": [ { "field": "quantity", "issue": "must be > 0" } ]
  },
  "request_id": "uuid"
}
```

### 4.3 Standard error codes

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `NOT_FOUND` | 404 | Entity does not exist |
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Valid token, insufficient permission |
| `CONFLICT` | 409 | Business rule violation |
| `INSUFFICIENT_STOCK` | 409 | Stock would go negative |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### 4.4 Pagination

All list endpoints accept: `?page=1&per_page=25&sort=created_at&order=desc&search=...`

### 4.5 Key API modules

```
/api/v1/auth/          login, logout, refresh, me, change-password
/api/v1/admin/         users, roles, permissions, settings
/api/v1/customers/     CRUD + contacts + addresses + 360 view
/api/v1/vendors/       CRUD + contacts + bank details
/api/v1/products/      CRUD + variants + pricing + images
/api/v1/inventory/     transactions, balance, lots, transfers, adjustments
/api/v1/purchase/      requisitions, orders, entries, returns
/api/v1/sales/         quotations, orders, deliveries, invoices, returns
/api/v1/production/    lots, stages, fabric-runs, material-issues, outputs
/api/v1/finance/       receipts, payments, expenses, ledger, aging
/api/v1/gst/           tax-rates, hsn, reports
/api/v1/reports/       sales, purchase, inventory, production, finance, gst
/api/v1/agents/        chat (POST), history (GET), tools (GET)
/api/v1/health/        liveness, readiness
```

---

## 5. Authentication & Authorization

### 5.1 JWT flow

```
POST /api/v1/auth/login
  → access_token (15 min TTL, HS256)
  + refresh_token (30 day TTL, stored in httpOnly cookie)

POST /api/v1/auth/refresh
  → new access_token + rotated refresh_token

POST /api/v1/auth/logout
  → invalidates refresh_token (stored in Redis blacklist)
```

### 5.2 Token payload

```json
{
  "sub": "user-uuid",
  "email": "user@company.com",
  "company_id": "company-uuid",
  "roles": ["production_manager"],
  "permissions": ["production.view", "production.create"],
  "iat": 1234567890,
  "exp": 1234568790
}
```

### 5.3 Permission naming convention

`<module>.<action>` — all checked server-side, never trusted from frontend.

```
# Master Data
master_data.view  master_data.create  master_data.edit  master_data.delete

# CRM
crm.view  crm.create  crm.edit  crm.delete

# Sales
quotation.view  quotation.create  quotation.approve  quotation.cancel
sales_order.view  sales_order.create  sales_order.approve
delivery.view  delivery.create  delivery.dispatch
invoice.view  invoice.create  invoice.cancel

# Purchase
purchase_order.view  purchase_order.create  purchase_order.approve
purchase_entry.view  purchase_entry.create
purchase_return.view  purchase_return.create

# Inventory
inventory.view  inventory.receive  inventory.issue
inventory.transfer  inventory.adjust  inventory.opening_balance

# Production
production.view  production.create  production.start
production.log  production.complete  production.cancel

# Finance
finance.view  finance.receipt  finance.payment  finance.expense

# Reports
reports.sales  reports.purchase  reports.inventory
reports.production  reports.finance  reports.gst

# Administration
admin.users  admin.roles  admin.settings  admin.audit
```

### 5.4 Rate limiting

- Login: 5 attempts / 15 min per IP
- API: 300 req / min per authenticated user
- Agent chat: 30 req / min per user

---

## 6. Agent Architecture (LangGraph)

### 6.1 Design philosophy

> AI understands intent. Domain services hold authority.

Agents can **read** anything. Agents can **suggest** anything. Agents can **execute** only through typed tool functions that enforce business rules, permissions, and DB transactions. No agent ever calls raw SQL or bypasses the domain service layer.

### 6.2 LangGraph state

```python
class ERPAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    company_id: str
    permissions: list[str]
    intent: str | None
    specialist: str | None
    context: dict          # domain data fetched this turn
    pending_action: dict | None   # action awaiting user confirmation
    confirmed: bool
    response: str | None
```

### 6.3 Graph topology

```
START
  │
  ▼
[orchestrator_node]     ← intent detection, routing
  │
  ├──► [master_data_agent]
  ├──► [crm_agent]
  ├──► [sales_agent]
  ├──► [pricing_agent]
  ├──► [purchase_agent]
  ├──► [inventory_agent]
  ├──► [production_agent]
  ├──► [costing_agent]
  ├──► [finance_agent]
  ├──► [gst_agent]
  ├──► [reporting_agent]
  └──► [admin_agent]
         │
         ▼
  [confirmation_node]   ← for write operations, present action + ask confirm
         │
    ┌────┴────┐
    │confirmed│
    ▼         ▼
[execute]  [cancel]
    │
    ▼
[response_node]
    │
   END
```

### 6.4 Agent definitions

| Agent | Can Read | Can Suggest | Can Execute |
|-------|----------|-------------|-------------|
| **Orchestrator** | intent, routing | delegation | none |
| **Master Data** | customers, products, vendors | data corrections | create/update master records |
| **CRM** | leads, activities, pipeline | follow-up actions | create lead, log activity, update opportunity |
| **Sales** | quotations, orders, deliveries | pricing, delivery window | create quotation, convert to order |
| **Pricing** | price lists, cost sheets | price adjustments | none (suggest only) |
| **Purchase** | POs, receipts, vendor performance | reorder, vendor selection | create PO (with confirmation) |
| **Inventory** | stock, lots, movements | transfers, adjustments | create transfer/adjustment (with confirmation) |
| **Production** | lots, stages, WIP, material requirements | scheduling, material needs | log stage entry (with confirmation) |
| **Costing** | cost sheets, actuals vs planned | variance alerts | none (read + suggest only) |
| **Finance** | receivables, payables, aging | payment priorities | record receipt/payment (with confirmation) |
| **GST** | tax rates, HSN codes | classification | none |
| **Reporting** | all aggregated data | report generation | export CSV/Excel |
| **Admin** | users, roles | permission review | none |

### 6.5 Tool contract

Every agent tool must follow this contract:

```python
class ToolResult(BaseModel):
    success: bool
    data: dict | list | None
    error: str | None
    requires_confirmation: bool = False
    confirmation_summary: str | None = None  # shown to user before exec
    audit_action: str | None = None

async def tool_create_stock_transfer(
    params: StockTransferParams,
    user_id: str,
    permissions: list[str],
) -> ToolResult:
    # 1. Check permission
    if "inventory.transfer" not in permissions:
        return ToolResult(success=False, error="Permission denied")
    # 2. Validate via business rules
    result = await business_rules.validate_transfer(params)
    if not result.valid:
        return ToolResult(success=False, error=result.reason)
    # 3. If first call — return confirmation summary
    if not params.confirmed:
        return ToolResult(
            success=True,
            requires_confirmation=True,
            confirmation_summary=f"Transfer {params.qty} kg from {params.from_wh} to {params.to_wh}",
        )
    # 4. Execute via domain service inside a DB transaction
    transfer = await inventory_service.create_transfer(params, user_id)
    # 5. Write audit log
    await audit_service.log("inventory_transfer", transfer.id, user_id)
    return ToolResult(success=True, data=transfer.dict())
```

---

## 7. Business Rules Engine

A dedicated `BusinessRulesEngine` class sits between agent tools/domain services and the database. It enforces hard rules that can never be overridden:

```python
# Inventory rules
cannot_issue_more_than_available_stock()
cannot_transfer_to_same_warehouse()
cannot_adjust_locked_period()

# Sales rules
cannot_deliver_more_than_ordered()
cannot_convert_cancelled_quotation()
cannot_invoice_without_delivery()

# Production rules
cannot_close_lot_with_incomplete_stages()
cannot_issue_more_material_than_bom_without_variance_permission()
cannot_reopen_completed_production_lot()

# Finance rules
cannot_delete_financial_transaction()
cannot_modify_completed_payment()

# General
cannot_backdate_more_than_allowed_days()  # configurable per company
cannot_approve_own_transaction()          # if SoD enabled
```

Rules are Python functions, not LLM instructions. They execute deterministically.

---

## 8. Inventory Ledger Service

```python
class InventoryService:
    async def receive(self, params: ReceiveParams, user_id: str) -> InventoryTransaction
    async def issue(self, params: IssueParams, user_id: str) -> InventoryTransaction
    async def transfer(self, params: TransferParams, user_id: str) -> tuple[InventoryTransaction, InventoryTransaction]
    async def adjust(self, params: AdjustParams, user_id: str) -> InventoryTransaction
    async def get_balance(self, product_id: UUID, warehouse_id: UUID) -> Decimal
    async def get_ledger(self, product_id: UUID, **filters) -> list[InventoryTransaction]
    async def get_lot_trace(self, lot_id: UUID) -> LotTraceability
```

Every method:
1. Validates through `BusinessRulesEngine`
2. Opens a DB transaction (serializable isolation for stock operations)
3. Inserts an immutable `inventory_transactions` record
4. Refreshes `inventory_balance` materialised view
5. Writes audit log
6. Returns the created transaction

**Negative stock protection:** Configurable per company. If enabled, `issue()` and `transfer_out()` raise `INSUFFICIENT_STOCK` if balance < quantity.

---

## 9. Pricing Engine

All pricing is computed by a deterministic `PricingService`. The LLM never calculates prices.

```python
class PricingService:
    async def get_price(
        self,
        product_id: UUID,
        variant_id: UUID | None,
        customer_id: UUID | None,
        quantity: Decimal,
        date: date,
    ) -> PriceResult

    async def calculate_cost_sheet(
        self,
        product_id: UUID,
        components: list[CostComponent],
    ) -> CostSheet

    async def calculate_order_total(
        self,
        items: list[OrderItem],
        customer_id: UUID,
        date: date,
    ) -> OrderTotal
```

Price resolution priority:
1. Customer-specific + variant-specific price (exact match)
2. Customer-specific product price
3. Customer's price list (quantity slab)
4. Default price list
5. MRP (fallback)

Historical snapshots: price used on a quotation/order is frozen at creation time. Changing a price list never retroactively alters existing documents.

---

## 10. GST / Tax Engine

Tax is determined server-side based on:

```
(customer state == company state) → CGST + SGST
(customer state != company state) → IGST
(customer is export / SEZ)        → 0% / LUT
```

HSN code → GST rate is looked up from `hsn_codes` table. Rates are configurable; changing a rate never affects historical invoices (rate is snapshotted on the invoice line item at creation).

```python
class TaxService:
    async def determine_tax(
        self,
        product_id: UUID,
        customer_id: UUID,
        transaction_date: date,
        taxable_value: Decimal,
    ) -> TaxBreakdown  # → {cgst, sgst, igst, cess, total}
```

---

## 11. Production Traceability

The system maintains a complete chain:

```
inventory_lot (raw material)
    │
    └─► production_lots (garment lot)
            │ (via material_issues)
            └─► production_outputs
                    │
                    └─► inventory_transactions (finished goods)
                             │
                             └─► delivery_items
                                      │
                                      └─► sales_orders
                                               │
                                               └─► customers
```

Query: "Which customers received garments made from fabric lot FL-2026-042?"
→ Join chain: `inventory_lot → material_issues → production_lots → production_outputs → inventory_transactions → delivery_items → invoices → customers`

### 11.1 Style Master (Production Blueprint)

Full specification: `docs/Garments_ERP_Style_Master_Specification.md` — treat it as the source of truth; do not simplify or remove its concepts without explicit business-owner approval.

**Core principle:** `Style Master = what/how a garment is supposed to be produced`; `LOT = actual execution of that Style`. A LOT must snapshot the Style's configuration at creation time — editing a Style later must never retroactively change an already-created LOT.

```
STYLE MASTER
  ├── Basic Information (name, code, garment type, gender, season, final_output_unit)
  ├── Sizes & Colours (style_sizes / style_colours → Size Master / Colour Master) → SKU = Style + variant dimensions
  ├── Yarn Requirements (style_yarns → references inventory_lots as the Yarn Master)
  ├── Fabric Requirements (style_fabrics → references inventory_lots as the Fabric Master)
  ├── Production Workflow (style_processes) — a CONFIGURABLE, ordered, addable/removable list.
  │     Never a fixed universal sequence: each process carries its own
  │     tolerance_pct, input_unit, output_unit, conversion_rule, min/max/planned_rate,
  │     and an ordered list of sub-processes (style_sub_processes) e.g. Stitching → Power Table / Snitex / Helpers.
  ├── Trim Planning (style_trims → references inventory_lots as the Trim Master; category: Sizable / Non-Sizable)
  └── Packing Material Planning (style_packing_materials; consumption_stage e.g. "After Ironing")
        │
        │  POST /production/lots (style_id = ...)
        ▼
PRODUCTION LOT (snapshot, frozen at creation)
  ├── final_output_unit, style_version  — copied from the Style at creation time
  └── production_stages — one row per ENABLED style_process (ordered by seq), each carrying its own
        frozen tolerance_pct / input_unit / output_unit / conversion_rule / min_rate / max_rate / planned_rate
        (columns on production_stages, not a live join back to style_processes)
```

**Why stages are snapshotted, not referenced live:** `ProductionService.create_lot()` copies each enabled `StyleProcess`'s fields onto a new `ProductionStage` row at LOT-creation time (`style_process_id` is kept only as provenance, not as the source of truth for tolerance/units/rates). This is what makes "edit Style → LOT unaffected" hold: the LOT's stages are independent rows from the moment they're created. If a Style has no configured processes (or no `style_id`), `create_lot()` falls back to a generic 5-stage sequence (Cutting/Making/Finishing/QC/Packing) so the LOT is still usable — this fallback is the *only* place anything resembling a fixed workflow exists, and only for Styles that were never given a real process list.

**Do-not-regress list** (mirrors the spec's guardrails — check before touching this area):
- Don't hard-code one universal process sequence for all Styles.
- Don't hard-code one global tolerance % — it's per-process (`style_processes.tolerance_pct`).
- Don't assume Pieces is the only unit anywhere in the workflow — units are per-process (`input_unit`/`output_unit`) and the Style's `final_output_unit` is one of Pieces/Dozen/Sets/Boxes.
- Don't let a Style edit change an existing LOT's stages — LOTs must keep reading their own `production_stages` snapshot, never re-deriving from `style_processes` after creation.
- Don't turn yarn/fabric/trim references back into free text — they link to `inventory_lots` (the materials masters) via `lot_id`.

API: `POST /production/styles` (creates the full nested blueprint in one transaction), `GET /production/styles`, `GET /production/styles/{id}` (full detail). Frontend: `/production/styles`, `/production/styles/new` (7-section form), `/production/styles/[id]`.

---

## 12. Background Jobs (Celery + Redis)

| Job | Trigger | Action |
|-----|---------|--------|
| `refresh_inventory_balance` | After each stock transaction | Refresh materialised view |
| `generate_report` | On demand | Async report generation |
| `send_low_stock_alert` | Scheduled (every 6h) | Check reorder levels, notify |
| `send_overdue_payment_alert` | Scheduled (daily) | AR aging check |
| `expire_refresh_tokens` | Scheduled (hourly) | Clean Redis blacklist |
| `generate_invoice_pdf` | After invoice creation | PDF generation + S3 upload |
| `process_bulk_import` | After CSV upload | Validate + insert master data |

---

## 13. File / Image Storage

- Local development: local filesystem at `/media/`
- Production: S3-compatible object storage (configurable via env)
- Accepted types: JPG, PNG, PDF, XLSX, CSV
- Max upload size: 10 MB per file
- Virus scanning: optional (configurable)
- Files referenced by `file_attachments` table (entity_type + entity_id polymorphic)

---

## 14. Frontend Structure (Next.js App Router)

```
frontend/src/
  app/
    (auth)/
      login/page.tsx
      forgot-password/page.tsx
    (app)/
      layout.tsx             ← sidebar + topbar shell
      dashboard/page.tsx
      crm/
        page.tsx             ← customer list
        [id]/page.tsx        ← customer 360
      sales/
        quotations/
        orders/
        deliveries/
        invoices/
      purchase/
        orders/
        entries/
        returns/
      inventory/
        page.tsx             ← stock dashboard
        [material-type]/page.tsx
      production/
        lots/
        fabric-runs/
      finance/
        receipts/
        payments/
        outstanding/
      reports/
      admin/
        users/
        roles/
        settings/
      ai-assistant/page.tsx
  components/
    ui/                      ← shadcn/ui primitives
    layout/
      sidebar.tsx
      topbar.tsx
      command-palette.tsx    ← ⌘K global search
    shared/
      data-table.tsx         ← reusable table with filters/sort/export
      status-badge.tsx
      timeline.tsx
      kpi-card.tsx
      stock-card.tsx
      empty-state.tsx
      skeleton-loader.tsx
    forms/
      form-field.tsx
      autocomplete.tsx
  lib/
    api.ts                   ← Axios instance + interceptors
    auth.ts                  ← token management
    query-client.ts          ← TanStack Query setup
    utils.ts
  types/
    api.ts                   ← shared API response types
    domain.ts                ← domain entity types
```

### UX principles (inspired by Kamna, substantially upgraded)

- Every entity has a full detail page with tabs: Overview · Transactions · Documents · Activity
- All list pages: searchable, filterable, sortable, exportable, with saved views
- Create flows: quick-create modal (2–3 fields) → full detail page for the rest
- Write operations from AI agent always show a confirmation summary before executing
- Skeleton loaders on all async fetches
- Optimistic updates where safe (status changes, simple field edits)
- ⌘K command palette for global navigation + search
- Unsaved changes warning on complex forms
- All destructive actions require a typed confirmation (e.g. "type lot name to close")

### Known frontend gotchas

- **`position: fixed` inside page content is NOT viewport-relative.** `globals.css` has `main > * { animation: fade-in 0.28s ease both; }` for the page-entrance effect. Because of `animation-fill-mode: both`, every page's root div permanently keeps `transform: translateY(0)` after the animation ends — and per the CSS spec, *any* non-`none` transform on an ancestor creates a new containing block for `position: fixed` descendants. A corner-anchored fixed element (e.g. `fixed bottom-6 right-6`) rendered inline inside a page's own JSX will silently position itself relative to the page's scrollable content instead of the real viewport — invisible below the fold on any page taller than the viewport. **Fix:** render such elements through `components/shared/modal-portal.tsx`'s `ModalPortal` (portals to `document.body`), the same pattern already used for `ModalShell` and other overlays. Don't "fix" this by editing the global animation rule — other pages may depend on it.
- **Statically-prerendered pages must not call `new Date()` (or anything else non-deterministic) directly in JSX.** Pages without dynamic route params (e.g. `/dashboard`) are prerendered at build time by default; a `new Date()` baked into that build-time HTML will always mismatch the client's real time on hydration. Don't paper over the resulting hydration warning with `suppressHydrationWarning` — React then trusts the server value *permanently* and the element never updates again (worse than the warning). Instead, gate the dynamic value behind a `useState`/`useEffect` mount check so both the server and the pre-mount client render a stable placeholder, and the real value appears only after mount.

---

## 15. Testing Strategy

| Layer | Tool | What |
|-------|------|------|
| Backend unit | pytest + pytest-asyncio | Domain services, business rules, pricing, tax calculations |
| Backend integration | pytest + httpx + testcontainers | API endpoints against real PostgreSQL |
| Inventory ledger | pytest | All stock movement scenarios + concurrent writes |
| Agent tools | pytest | Tool contract, permission checks, confirmation flow |
| Security | pytest | Auth bypass, IDOR, SQL injection, token expiry |
| Frontend unit | Vitest + Testing Library | Components, hooks, form validation |
| E2E | Playwright | Critical paths: login, create quotation, receive stock, log production |

### Critical test cases

```python
# Inventory integrity
test_receive_100_issue_20_transfer_30_return_5_expect_55()
test_concurrent_stock_deduction_no_oversell()
test_negative_stock_blocked_when_protection_enabled()

# Pricing
test_customer_specific_price_overrides_list_price()
test_quantity_slab_pricing_correct_break()
test_gst_cgst_sgst_same_state()
test_gst_igst_different_state()

# Business rules
test_cannot_deliver_more_than_ordered()
test_cannot_approve_own_quotation_with_sod_enabled()
test_agent_cannot_bypass_permission_check()
test_agent_cannot_execute_without_confirmation()
```

---

## 16. Docker Architecture

```yaml
services:
  nginx:      reverse proxy, SSL termination, static files
  frontend:   Next.js (standalone build)
  backend:    FastAPI (uvicorn, 4 workers)
  worker:     Celery worker (same image as backend)
  postgres:   PostgreSQL 16 with persistent volume
  redis:      Redis 7 (sessions, cache, queue)
```

Dev: `docker-compose.yml` — hot reload, local volumes  
Prod: `docker-compose.prod.yml` — multi-stage builds, no dev tools

### NGINX routing

```nginx
/             → frontend:3000
/api/         → backend:8000
/ws/          → backend:8000 (WebSocket for agent streaming)
/media/       → local file storage
```

---

## 17. Deployment Architecture

```
Internet
  │
  ▼
[NGINX] :443 (HTTPS) / :80 → 443 redirect
  │
  ├─► [Frontend] :3000   Next.js standalone
  ├─► [Backend]  :8000   FastAPI / uvicorn
  │     └─► [Worker]     Celery (same container image)
  │
  ├─► [PostgreSQL] :5432  Persistent volume + daily backup
  └─► [Redis]      :6379  Append-only persistence
```

Secrets managed via `.env` files (never committed). Production secrets via environment injection or Vault.

---

## 18. Implementation Phases (Execution Order)

| Phase | Deliverable | Blocks |
|-------|-------------|--------|
| 1 | Folder structure + Docker + DB migrations + FastAPI shell + Next.js shell | All |
| 2 | Auth (JWT/RBAC) + Admin (Users/Roles) | 3–14 |
| 3 | Master Data (Customer, Product, Vendor, Price) | 4–14 |
| 4 | Inventory Ledger (Yarn, Fabric, Trim, FG) | 5, 6, 9 |
| 5 | Purchase (PO → Receipt → Inventory) | 9, 10 |
| 6 | CRM + Sales (Quotation → Order → Delivery → Invoice) | 9, 10 |
| 7 | Pricing + Costing Engine | 6, 8 |
| 8 | Production (Lots, Stages, Material Issue, Output) | 9, 10 |
| 9 | Production Cost Tracking | 10, 12 |
| 10 | Finance (Receipts, Payments, Aging) | 12 |
| 11 | GST Engine | 6, 10 |
| 12 | Reports + Analytics | — |
| 13 | LangGraph AI Agents | — |
| 14 | Natural Language ERP Interface | 13 |
| 15 | Premium UI/UX polish | — |
| 16 | Testing + Security hardening | — |
| 17 | Docker + NGINX production config | — |
| 18 | Final audit + production readiness | — |

---

## 19. Decisions That Must Stay Stable

1. **Inventory is a ledger.** Never add a `current_stock` mutable field to products.
2. **Money is NUMERIC(15,2).** Never use FLOAT for currency.
3. **Tax is backend-only.** Frontend never calculates GST.
4. **Agents confirm before writing.** Every tool that mutates data must return `requires_confirmation=True` on first call.
5. **Historical documents are immutable.** Closed invoices, completed production lots, and settled payments cannot have their financial values changed.
6. **Permissions are checked server-side.** Frontend visibility is a UX convenience only.
7. **Document sequences are DB-level atomic.** Use `SELECT ... FOR UPDATE` on `document_sequences` to prevent duplicate numbers.
8. **UUID primary keys everywhere.** No auto-increment integers exposed in URLs.
