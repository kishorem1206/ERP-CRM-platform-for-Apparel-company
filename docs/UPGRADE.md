# CRM/ERP Upgrade Plan
**Date created:** 2026-08-29
**Author:** Kishore

---

## Overview

Progressive upgrade of the existing Apparel Manufacturing CRM/ERP into a complete textile manufacturing ERP — covering Lots, Fabric Runs, Yarn, Fabric, Trims, Inventory, Production, Procurement, Buyers/Orders, Staff/Permissions, Dashboards, Reporting, and AI.

**Core rule:** Do NOT rebuild the existing application. Extend and enhance it phase by phase.

---

## Phase Sequence

| Phase | Topic | Status |
|-------|-------|--------|
| 0 | Complete Existing CRM/ERP Audit | ✅ Complete — 2026-08-29 |
| 1 | Database & Domain Foundation | ✅ Complete — 2026-08-29 |
| 2 | Create Workflow Shell | ✅ Complete — 2026-08-30 |
| 3 | New Lot | ✅ Complete — 2026-08-30 |
| 4 | New Fabric Run | ⬜ Pending |
| 5 | Add Yarn | ⬜ Pending |
| 6 | Add Fabric | ⬜ Pending |
| 7 | Add Trims | ⬜ Pending |
| 8 | Inventory / Stock Engine | ⬜ Pending |
| 9 | Production Lifecycle | ⬜ Pending |
| 10 | Suppliers / Procurement | ⬜ Pending |
| 11 | Buyers / Orders / Sales | ⬜ Pending |
| 12 | Staff / Permissions / Approvals | ⬜ Pending |
| 13 | Dashboards / Reports | ⬜ Pending |
| 14 | AI / Assistant / Intelligence | ⬜ Pending |
| 15 | Validation / Testing / Security | ⬜ Pending |
| 16 | Final ERP Integration & Production Readiness | ⬜ Pending |

---

## Session Log

### Session 1 — 2026-08-29
- Phase 0 audit initiated
- Related docs: `ERP_UPGRADE_AUDIT.md`

---

## Master Session Rules (paste at start of every session)

```
IMPORTANT SESSION RULES

This is an existing production-oriented CRM + ERP application.

You are modifying an existing system, NOT creating a new application.

Before making changes:

1. Read /docs/ERP_UPGRADE_AUDIT.md
2. Read /docs/ERP_UPGRADE_PROGRESS.md
3. Inspect the current implementation related to this phase.
4. Do not assume previous implementation is correct.
5. Verify the current database schema.
6. Verify existing APIs.
7. Verify existing frontend components.

Never:
- delete existing production data
- reset the database
- replace the application architecture without justification
- create duplicate entities / tables / APIs
- bypass existing authentication or authorization
- trust frontend validation
- modify stock without an auditable transaction
- calculate financial values only on the frontend
- use frontend counters for unique numbers
- claim tests passed without actually running them.

Preserve the existing UI/design language.
```

---

## Phase Prompts

### PHASE 0 — COMPLETE EXISTING CRM/ERP AUDIT

```
I already have a functioning CRM + ERP application.

I do NOT want you to rebuild it.

I want to progressively upgrade the existing system into a complete textile manufacturing CRM/ERP
while preserving the existing design, architecture, data and working functionality.

This is PHASE 0: SYSTEM AUDIT ONLY.

Do NOT implement major features yet.

Your job in this phase is to completely understand the existing system before we modify it.

==================================================
1. INSPECT THE ENTIRE PROJECT
==================================================

Inspect the complete repository.

Understand:
- Frontend framework
- Backend framework
- API architecture
- PostgreSQL database
- ORM / migrations
- authentication / authorization
- tenant/company structure
- existing CRM modules
- existing ERP modules (inventory, production, buyers, suppliers, staff, styles, orders, reports,
  dashboard, AI functionality, file/document handling, notifications, configuration, deployment)

Do not assume anything. Read the actual code.

==================================================
2. DATABASE AUDIT
==================================================

Inspect the complete PostgreSQL schema.

Document: tables, columns, PKs, FKs, indexes, unique constraints, enums, relationships,
nullable fields, audit fields, soft deletion, tenant/company relationships.

Identify existing entities that correspond to:
companies, users, staff, buyers, suppliers, styles, orders, lots, production,
yarn, fabric, trims, inventory, stock, warehouses, transactions, costing,
invoices, delivery, purchasing.

Do not create duplicate entities if equivalent entities already exist.

==================================================
3. BACKEND AUDIT
==================================================

Inspect: routes, controllers, services, repositories, schemas, DTOs, validation,
authentication, authorization, database transactions, error handling.

Map: Frontend → API → Backend → Database for every major existing module.

==================================================
4. FRONTEND AUDIT
==================================================

Inspect: layouts, navigation, pages, modals, forms, tables, dialogs, reusable components,
design system, state management, API client, validation, loading states, error states.

DO NOT introduce a new design system.
The future features must look native to the existing application.

==================================================
5. EXISTING FUNCTIONALITY
==================================================

Create a list of everything that currently works.
For each feature document: Feature, Location, Frontend, Backend, Database, API,
Dependencies, Current limitations.

==================================================
6. GAP ANALYSIS
==================================================

Compare the existing system against the following target workflows:

PRODUCTION: New Lot, New Fabric Run
STOCK: Add Yarn, Add Fabric, Add Trims

Identify: already implemented / partially implemented / missing / conflicting /
needs database changes / needs backend changes / needs frontend changes.

==================================================
7. DO NOT MODIFY YET
==================================================

This phase is audit only. Do NOT delete data, reset database, rewrite architecture,
replace working components, create duplicate tables/APIs, redesign, or migrate data.

==================================================
8. FINAL AUDIT REPORT
==================================================

Produce:
A. Current architecture
B. Database ER/domain map
C. Frontend architecture
D. Backend architecture
E. Existing modules (inventory, production, CRM, auth/permissions)
F. Gap analysis
G. Recommended implementation sequence
H. Files that will probably need modification
I. Tables that will probably need modification
J. New tables that may be required
K. Risks
L. Things that absolutely must NOT be changed

Save to: /docs/ERP_UPGRADE_AUDIT.md
```

---

### PHASE 1 — DATABASE & DOMAIN FOUNDATION

```
This is PHASE 1 of the CRM/ERP upgrade.

Read: /docs/ERP_UPGRADE_AUDIT.md

We are now building the domain/database foundation.

IMPORTANT: Do NOT rebuild the existing application. Extend the existing architecture.
Do not destroy existing data. Do not create duplicate entities.

OBJECTIVE: Prepare the PostgreSQL database and backend domain model required for:
Lots, Styles, Fabric Runs, Yarn, Fabric, Trims, Suppliers, Material composition,
Inventory, Inventory transactions, Production relationships, Colour/Fabric/Trim variants.

Reuse existing entities wherever possible.

DATABASE PRINCIPLES: Use proper relational modelling. Do NOT create one giant materials table.
Separate: material identity / technical attributes / composition / inventory / inventory movements
/ production relationships where appropriate.

NUMBER GENERATION: Lot, run, yarn, fabric, trim numbers must support optional manual numbers.
Backend generates unique numbers when blank. Generation must be concurrency-safe.
Never use existing_count + 1. Add database uniqueness constraints.

COMPOSITION: Create/reuse a proper composition model. Support one fibre and blend.
Validate: sum = 100%. Do not store blends as a string.

INVENTORY FOUNDATION: Prepare the data model for inventory movements.
Support: RECEIPT, ISSUE, TRANSFER, ADJUSTMENT, RETURN, CONSUMPTION.
Every inventory change must be auditable.

COLOUR/VARIANT FOUNDATION: Prepare the model for Fabric (colour, dia, qty/weight)
and Trim (colour, quantity) since "Split by colour and dia" and "Split by colour"
options appear in the UI.

MIGRATIONS: Create proper migrations. Before migration: inspect current schema,
ensure no conflicts, preserve existing data. After migration: verify schema, FKs,
indexes, constraints.

BACKEND: Create or modify domain models/services as required.
Do not create unnecessary endpoints yet. Focus on a clean foundation.

TESTING: Test migrations, constraints, relationships, number uniqueness,
composition validation, rollback behavior, existing functionality.

DOCUMENTATION: Update /docs/ERP_UPGRADE_PROGRESS.md
```

---

### PHASE 2 — CREATE WORKFLOW SHELL

```
This is PHASE 2.

Read: /docs/ERP_UPGRADE_AUDIT.md and /docs/ERP_UPGRADE_PROGRESS.md

Now implement the CREATE workflow framework.

CREATE BUTTON: The existing sidebar should have a "Create" button.
Clicking Create opens a modal with sections:

PRODUCTION:
- New lot — Start a production run
- New fabric run — Track yarn through knitting, dyeing, finishing

STOCK:
- Add yarn — Receive yarn into stock
- Add fabric — Receive fabric into stock
- Add trims — Trims & accessories into stock

UI: Use the existing application's design system. Do not introduce a separate design language.
Match the supplied screenshots: modal, rounded corners, spacing, typography, cards, icons,
buttons, sections, responsive behavior, dimmed background.

REUSABLE COMPONENTS: Create reusable components where appropriate:
CreateModal, FormModal, ScrollableModal, TextField, NumberField, DateField,
SearchSelect, PillSelect, SegmentedControl, MultiSelect, CurrencyField.
Reuse existing components if equivalent ones already exist.

WORKFLOW: Click Create → [option] opens the corresponding form.
For now forms can be placeholders if detailed implementation belongs to later phases.

IMPORTANT: Must be integrated into existing navigation. Do not break any existing functionality.

TEST: Verify every Create option opens correctly. Verify modal closing.
Verify responsive behavior. Verify no existing navigation is broken.
```

---

### PHASE 3 — NEW LOT

```
This is PHASE 3. Read audit and progress documents first.

Implement the COMPLETE New Lot workflow.

FORM: Create → New lot
Fields:
- Lot number (optional, auto-generate when blank, unique)
- Style (search/select existing Style)
Button: Create lot

BACKEND: Create proper API/service with authentication, authorization,
validation, style relationship, number generation, duplicate prevention,
database transaction.

DATABASE: Persist the lot. Ensure lot → style relationship exists.
Preserve compatibility with existing production functionality.
Architecture must allow lot to later contain: pieces, delivery date,
order reference, production stages, materials, quantities, costing,
buyer/order relationships.

TEST: Manual number, auto-generated number, duplicate number, existing style selection,
invalid style, unauthorized request, database rollback, refresh and verify persistence,
existing lot functionality.
```

---

### PHASE 4 — NEW FABRIC RUN

```
This is PHASE 4. Read all previous documentation first.

FORM: Create → New fabric run
Fields:
- Run number (optional, auto-generate when blank)
- Construction (Single jersey, Fleece...)
Button: New run

DATA MODEL: Fabric Run must be a proper production entity.
Must eventually support: Run → Knitting → Dyeing → Finishing.
Do not implement as a simple notes field.

BACKEND: POST fabric run with validation, authentication, authorization,
number generation, duplicate prevention, transaction handling.

DATABASE: Persist: run number, construction, status, timestamps,
tenant/company, creator, future production relationships.
Reuse existing production entities if present.

TEST: Manual/automatic/duplicate number, construction, database persistence,
API validation, authorization, rollback, existing production functionality.
```

---

### PHASE 5 — ADD YARN

```
This is PHASE 5. Implement the complete Add Yarn workflow.
Read all previous implementation documents. Do not simplify the form.

FORM: Create → Add yarn (scrollable modal)

BASIC INFORMATION:
- Yarn number (optional, auto-generate when blank)
- Supplier
- Invoice number
- Date

TECHNICAL INFORMATION:
- Count
- Ply: Single / 2 ply / 3 ply / Other
- Mill
- Spinning/type: Ring / Open end / Vortex
- Treatment: Compact / Gassed / Mercerised

COMPOSITION:
Segment: One fibre | Blend
One fibre: Cotton / Polyester / Viscose / Modal / Lycra
Blend: multiple fibres + percentages. Validate: total = 100%.
Use relational storage.

STATE: Greige | Dyed. Support colour where applicable.

QUANTITY:
- Bags
- Kg per bag
- Weight kg
- Rate per kg
- Value (calculated: weight × rate — backend must recalculate/validate)
- Comments

RECEIVE button: One atomic transaction:
1. validate → 2. create yarn → 3. create inventory receipt
→ 4. create inventory ledger movement → 5. update/derive stock
→ 6. store cost → 7. store supplier/invoice → 8. commit
ROLLBACK EVERYTHING on any failure.

TEST: Complete workflow from browser to PostgreSQL.
Verify: Yarn, Inventory receipt, Inventory transaction, Stock balance after refresh.
Test: invalid composition, invalid quantity, duplicate yarn number, rollback,
concurrent number generation, unauthorized user.
```

---

### PHASE 6 — ADD FABRIC

```
This is PHASE 6. Implement complete Add Fabric workflow.

BASIC: Fabric number, Supplier, Invoice number, Date

COMPOSITION: One fibre | Blend (Cotton/Polyester/Viscose/Modal/Lycra)
Blend: fibre + percentage. Total = 100%.

CONSTRUCTION: Knit | Woven
Knit: Single Jersey, Interlock, Rib, French Terry, Fleece, Pique, More, Other
("Other" supports custom construction)
Woven: appropriate extensible construction model.

TECHNICAL: GSM, Dia, Dia unit (in)

COLOUR: Colour, optional "Split by colour and dia" (persist this — affects downstream cutting)

FINISH: Bio wash, Enzyme wash, Silicone wash, Peach, Brushed, Compacted,
Sanforized, Calendered, Mercerised, Singed. Allow multiple.

RECEIVING: Atomic transaction: validate → create fabric → inventory receipt
→ inventory movement → update stock → persist all attributes → commit.

TEST: composition, construction, GSM, Dia, colour, finish, split by colour/dia,
duplicate number, rollback, inventory quantity.
```

---

### PHASE 7 — ADD TRIMS

```
This is PHASE 7. Implement complete Add Trims workflow.

BASIC: Trim number, Supplier, Invoice number, Date

TYPE: Label, Tag, Button, Elastic, Poly, Box, More (extensible)

UNIT: Pieces / Gross / Dozen / Metre / Kilogram (persisted — not generic number)

DETAILS: Brand, Colour, optional "Split by colour" (affects dispatch behavior)

QUANTITY/COST: Description, Quantity, Cost per unit,
Total value (calculated — backend must recalculate/validate)

RECEIVING: Atomic transaction: create trim → inventory receipt
→ inventory movement → update stock → persist unit/cost/supplier/colour/audit trail.

TEST: Every unit, colour split, inventory, rollback, duplicate number, authorization.
```

---

### PHASE 8 — INVENTORY / STOCK ENGINE

```
This is PHASE 8. Make inventory an ERP-grade stock system.

TRANSACTION TYPES: RECEIPT, ISSUE, CONSUMPTION, TRANSFER, ADJUSTMENT, RETURN

INVENTORY LEDGER: Every movement contains:
material, material type, quantity, unit, direction, transaction type, reference,
warehouse/location, date/time, user, cost, source, destination, notes.

STOCK: Safely derived or maintained consistently from transactions.
Never allow unexplained stock changes.

MATERIAL TYPES: Yarn, Fabric, Trims. Architecture must allow future types.

AUDIT: Users must be able to answer:
Where did this stock come from? Where did it go? Who changed it? When? Why? At what cost?

TEST: receive, issue, transfer, adjustment, rollback, negative stock,
concurrency, duplicate requests, decimal quantities, different units.
```

---

### PHASE 9 — PRODUCTION LIFECYCLE

```
This is PHASE 9. Connect Lot, Fabric Run, Yarn, Fabric into real production workflow.

TARGET: Lot → Production → Fabric Run → Knitting → Dyeing → Finishing
→ Fabric → Cutting → Garment/finished production

LOT: Eventually connects to style, buyer/order, quantity, delivery date,
production, materials, production status.

FABRIC RUN: Run number, Construction, Lot relationship, Production status,
Quantities, Material consumption, Output.

MATERIAL CONSUMPTION: When production consumes yarn/fabric, inventory must
decrease through an inventory transaction (never directly overwrite stock).

OUTPUT: When production generates fabric, inventory receives the output through a transaction.
Traceability: Input yarn → Fabric run → Fabric output.

STATUS: Proper production states. No arbitrary invalid transitions.

TEST: Lot creation, Fabric Run, Yarn consumption, Fabric generation,
Inventory decrease, Inventory increase, Traceability, Rollback.
```

---

### PHASE 10 — SUPPLIERS + PROCUREMENT

```
This is PHASE 10. Upgrade existing supplier/procurement functionality.
First inspect what already exists. Do not duplicate it.

SUPPLIER: Support appropriate supplier information.
Integrate with: Yarn, Fabric, Trims, Purchases, Invoices, Payments.

PROCUREMENT: Design/reuse: Purchase request, Purchase order,
Goods receipt, Invoice, Inventory receipt.

FLOW: Supplier → Purchase Order → Goods Receipt → Inventory Receipt → Stock → Invoice

IMPORTANT: Add Yarn/Add Fabric/Add Trims forms must remain useful.
Support both direct receipt and PO-based workflows.

TEST: Verify supplier → material → inventory traceability.
```

---

### PHASE 11 — BUYERS / SALES / ORDERS

```
This is PHASE 11. Upgrade CRM + ERP relationship between:
Buyer, Style, Order, Lot, Production, Delivery.

First inspect existing implementation. Do not duplicate existing modules.

TARGET: Buyer → Order → Style → Lot → Production → Fabric
→ Finished Goods → Dispatch → Delivery

ORDER: Support order reference, buyer, style, quantity, delivery date, priority, status.
Reuse existing order functionality if present.

LOT: Traceable back to Buyer, Order, Style where applicable.

TEST: Verify existing CRM behavior. Verify ERP production relationship.
No duplicate customer/buyer/order records.
```

---

### PHASE 12 — STAFF + PERMISSIONS + APPROVALS

```
This is PHASE 12. Upgrade authorization and staff permissions for ERP operations.
First inspect the existing permission system. Do not replace it unnecessarily.

ROLES: Determine existing roles. Consider: Admin, Management, Production,
Inventory, Purchase, Sales, Accounts, Staff.

PERMISSIONS: Control: Create lot, Create fabric run, Receive yarn/fabric/trims,
Issue inventory, Adjust inventory, Approve purchase, Edit supplier/material/production,
View financial data.

AUDIT: Important changes should record: user, timestamp, action, before, after.

TEST: Test unauthorized access through frontend AND direct API calls.
Frontend hiding is NOT security.
```

---

### PHASE 13 — DASHBOARDS + REPORTING

```
This is PHASE 13. Upgrade dashboards and reports using new ERP data.
Do not redesign the application unnecessarily.

DASHBOARD: Show: Open Lots, Production Progress, Yarn/Fabric/Trim Stock,
Pending Receipts, Production Runs, Upcoming Deliveries, Low Stock, Outstanding Orders.

REPORTS: Inventory report, Inventory movement, Material consumption, Production report,
Lot report, Fabric run report, Supplier purchases, Buyer orders, Delivery status, Material costing.

TRACEABILITY: Navigate: Lot → Production → Fabric Run → Materials → Inventory movements and reverse.

PERFORMANCE: Use pagination, filtering, aggregation, appropriate indexes.
```

---

### PHASE 14 — AI / ERP ASSISTANT

```
This is PHASE 14. Upgrade existing AI/assistant to understand ERP data.
Do not replace the existing AI system unnecessarily.

AI SHOULD ANSWER:
"How much yarn do we currently have?"
"Which lots are delayed?"
"Which fabric runs are open?"
"How much fabric did we produce this month?"
"Which supplier supplied this yarn?"
"Show me stock movement for this fabric."
"Which buyer orders are due next week?"
"Which materials are low in stock?"

IMPORTANT: AI must NOT invent database information.
Responses based on actual application data. Use appropriate backend tools/services.
For destructive operations: require proper authorization/confirmation.
```

---

### PHASE 15 — COMPLETE VALIDATION + TESTING

```
This is PHASE 15. Perform a complete ERP validation pass.
Do NOT add major new features. Find and fix problems.

FUNCTIONAL: Test every workflow from Phase 3 through Phase 13.
DATABASE: Verify FKs, unique constraints, indexes, transactions, rollback, data integrity,
decimal precision, null handling, tenant isolation.
SECURITY: authentication, authorization, API access, tenant isolation, IDOR,
unauthorized modification, frontend bypass, SQL injection, input validation.
CONCURRENCY: Simultaneous lot creation, yarn/fabric/trim receipt, inventory movement.
UI: desktop, tablet, mobile. Test all states: loading, error, empty, success, disabled,
duplicate, validation.
REGRESSION: Ensure all existing CRM features still work.

OUTPUT: /docs/ERP_FINAL_TEST_REPORT.md
```

---

### PHASE 16 — FINAL ERP INTEGRATION

```
This is PHASE 16. Perform final architectural integration review.
Make the application behave like ONE ERP, not disconnected modules.

TRACEABILITY: Verify complete chain:
Buyer → Order → Style → Lot → Production → Fabric Run → Yarn → Fabric
→ Finishing → Finished production → Inventory → Dispatch → Delivery

Also: Supplier → Purchase → Receipt → Inventory → Production consumption

DATABASE REVIEW: Find duplicate tables/fields, unused fields, redundant relationships,
missing indexes, missing constraints, inconsistent naming.
Do not make destructive changes without verifying existing data.

BACKEND REVIEW: Duplicated logic, inconsistent validation, transaction boundaries,
error handling, authorization, API naming, service boundaries.

FRONTEND REVIEW: Duplicated components, inconsistent forms/validation/loading/errors,
design inconsistencies. New screens must look like they belong to the existing CRM.

PERFORMANCE: Check N+1 queries, pagination, indexes, dashboard/inventory queries.

FINAL DOCUMENTATION: /docs/ERP_ARCHITECTURE_FINAL.md
Include: Architecture, DB model, API, Frontend, Inventory, Production, CRM,
Permissions, AI, Testing, Deployment, Known limitations, Future improvements.

FINAL RULE: Do not rewrite working parts merely for cosmetic reasons.
Goal: STABLE, MAINTAINABLE, AUDITABLE, SCALABLE, SECURE, PRODUCTION-READY.
```

---

*End of upgrade plan.*
