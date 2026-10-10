# GarmentOS — Production Module Reorganisation & Manufacturing Workflow Implementation

## 1. Objective

Reorganise and extend the existing GarmentOS CRM & ERP application to support a complete, traceable garment manufacturing workflow.

I have uploaded reference screenshots of an existing garment ERP order-planning system. Study every screenshot carefully. Use them to understand the functional requirements for:

- Size Break Up
- Style and Style Part configuration
- Fabric Requirement and Body Part mapping
- Yarn Planning
- Trims Planning
- Life Cycle and Process Tolerance
- Bill of Materials (BOM)
- Wages and Other Expenses
- Material allocation and production requirements

These screenshots are functional references. Do not blindly copy their outdated UI. Implement the same useful functionality using the existing application's design system, architecture, and components.

**This is an enhancement of the existing application, not a new application.**

The existing backend uses FastAPI and PostgreSQL. Inspect the actual repository to confirm the current stack, schema, and implementation before making changes.

The application already has masters and production functionality. Reuse existing Size Chart, Colour, Process, Yarn, Fabric, Trims, Packing Materials, Product/SKU, Supplier, Customer, and other relevant masters wherever available.

Do not create duplicate masters or parallel production workflows.

## 2. Mandatory execution rules

Before implementing anything, perform a complete audit.

### Audit the existing application

Inspect:

1. Frontend framework, routes, components, forms, tables, layouts, and design system.
2. Backend architecture, FastAPI routes, services, validation, and business logic.
3. PostgreSQL schema, ORM models, migrations, relationships, constraints, and indexes.
4. Existing authentication, roles, permissions, approval mechanisms, and audit history.
5. Existing order management, styles, SKUs, size charts, colours, fabric, yarn, trims, BOM, inventory, production lots, and production stages.
6. Existing APIs, status transitions, stock movements, calculations, reports, and notifications.
7. Existing tests, sample data, fixtures, and backward compatibility.
8. All uploaded reference screenshots, including their fields, tables, buttons, calculations, and workflow dependencies.

Search the entire codebase before creating a new entity, endpoint, master, or screen.

Produce an audit document containing:

- Existing implementation and file locations.
- Reusable components and entities.
- Existing functionality that already meets requirements.
- Missing or partially implemented functionality.
- Conflicting calculations or duplicate workflows.
- Required database changes.
- Migration and backward-compatibility risks.
- A phased implementation plan with dependencies.

**Phase 0 is audit and planning only. Do not modify application behaviour during this phase.**

After the audit, implement Phase 1 only. Stop and report the results before proceeding to the next phase. Do not attempt the entire project in one large change.

Maintain a checklist of completed, pending, and blocked requirements throughout the implementation.

---

# 3. Core manufacturing data hierarchy

The production system must support this hierarchy:

**Sales Order → Order Style → Style Part → Style Colour → Size → Planned Quantity → Material Requirements → Production Lot → Process Stage → Stage Output → Next Stage → Finished Goods Inventory → Dispatch**

Each relationship must be explicit in the database and available through the APIs.

For example:

Order: 10,000 shirts

- Style: Casual Shirt
- Style Parts: Front, Back, Collar, Sleeves, Cuffs
- Colours: Red, Blue, White
- Sizes: S, M, L, XL, XXL

Every combination must retain its own applicable quantity and material requirements.

A style part may use the same or different colours, fabrics, yarn compositions, trims, and processes. The system must not assume that every part uses the garment's primary colour or fabric.

Support shirts, trousers, dresses, and other garments through configurable style parts rather than hardcoded garment types.

## 4. Style Part Master and configuration

Add or extend a reusable **Style Part Master**.

Users must be able to:

- Select existing style parts from a searchable dropdown.
- Add a new custom style part directly from the form.
- Create, edit, activate, deactivate, and search style parts through the appropriate master screen.
- Reuse style parts across styles.
- Add garment-specific parts without requiring code changes.

Examples:

Shirt: Front, Back, Collar, Collar Band, Sleeves, Cuffs, Pocket, Placket.

Trouser: Front Panel, Back Panel, Waistband, Belt Loops, Pocket, Fly, Cuffs.

These are examples, not a fixed list.

For each order style, allow multiple parts. Each part must support its own:

- Part code and name.
- Applicable size chart.
- Colour assignments.
- Fabric assignment.
- Size-wise consumption.
- Applicable trims and accessories.
- Process routing.
- Tolerance configuration.
- Part-specific production quantities.

### Style SKU generation

Generate unique SKUs using the agreed format:

`SKU-Size-Colour`

Where necessary, extend the existing SKU structure to include a stable style-part identifier so that different parts do not collide.

For example:

`SHIRT-FRONT-M-RED`

`SHIRT-COLLAR-M-RED`

Use the existing SKU convention if the repository already has an established format. In either case, maintain uniqueness and backward compatibility.

## 5. Quantity model — critical requirement

**Do not use a single overall quantity as the working quantity in production stages.**

The overall order quantity may be displayed as a read-only summary, but operational quantities must be maintained by the relevant combination of:

- Order
- Style
- Style part
- Colour
- Size
- Production lot
- Stage

Every relevant screen must show the individual size quantities.

Example:

| Style Part | Colour | S | M | L | XL | Total |
|---|---|---:|---:|---:|---:|---:|
| Front | Red | 100 | 200 | 300 | 200 | 800 |
| Back | Red | 100 | 200 | 300 | 200 | 800 |
| Collar | Red | 100 | 200 | 300 | 200 | 800 |
| Front | Blue | 50 | 100 | 150 | 100 | 400 |

The total column is a calculated summary, not a substitute for size-wise records.

These figures are illustrative.

Support different quantities for different sizes, parts, and colours. Never infer a size distribution by dividing the total equally.

Validate that the relevant quantities reconcile with their parent order and part plan, allowing explicitly configured exceptions where business rules require them.

---

# 6. Production stages and page separation

The main production workflow must be organised into separate stage-specific screens.

The minimum required sequence is:

**Cutting → Checking → Packing → Completed (Consolidated)**

Other existing stages, including Knitting, Dyeing, Compacting, Printing, Stitching, Ironing, Checking, and Packing, must remain available where applicable to the configured production route.

Do not force every garment through every process. Use configurable process routing.

## Stage-specific screen behaviour

Each stage must have its own list, details, actions, validations, and permitted transitions.

- Cutting page: only work awaiting cutting, currently being cut, or ready for cutting completion.
- Checking page: only lots or quantities that have reached the checking stage.
- Packing page: only quantities cleared for packing.
- Completed page: consolidated completed quantities and their history.

The stage list must not display every order as if it were active at every stage.

Users should be able to filter by order, style, part, colour, size, production lot, date, status, and relevant warehouse or location.

Each stage should show:

- Order and production lot references.
- Style, part, colour, and size.
- Incoming quantity.
- Processed quantity.
- Accepted quantity.
- Rejected quantity.
- Pending quantity.
- Tolerance or variance, where applicable.
- Responsible user and timestamps.
- Next permitted action.

Maintain stage history. A stage transition must not erase or overwrite the prior stage's records.

Use a consistent stage-status model and prevent duplicate or invalid transitions.

---

# 7. Phase-by-phase implementation plan

## Phase 0 — Existing system audit

Deliver the audit document, entity mapping, dependency map, implementation checklist, and migration plan.

Identify which size and other masters already exist. Do not recreate them.

No functional code changes during this phase.

## Phase 1 — Size Chart and Style Part foundation

Inspect the existing Size Chart Master and Colour Master.

Reuse and extend them only where necessary.

Implement:

- Configurable size charts and size sequences.
- Size-wise quantity configuration.
- Style Part Master with dropdown selection and inline custom creation.
- Style-to-part relationships.
- Style-part-specific colour assignments.
- Unique SKU generation.
- Part-specific size quantity records.
- Validation and duplicate prevention.

The style creation screen must not contain production Input/Output fields.

Yarn is optional at style creation and must not be required unless an existing, justified business rule requires it.

Do not create an unnecessary yarn dependency merely because the garment uses fabric.

**Acceptance criteria:** A user can create a shirt style with multiple custom or existing parts, assign different colours and size quantities to each part, and generate unique SKUs without duplicating existing masters.

## Phase 2 — Fabric Requirement and Fabric Planning

Use the existing Fabric Master and existing fabric inventory.

Reference the screenshots' Fabric Requirement section, including fabric type, body part, count, fabric name, GSM, composition, weight, unit, and fabric diameter planning where applicable.

Implement:

- Fabric-to-style-part mapping.
- Fabric-to-body-part mapping.
- Size-wise fabric consumption.
- Fabric requirements by style, part, colour, and size.
- Fabric wastage percentages.
- Knit diameter and finish diameter where applicable.
- Fabric templates if supported by the current application.
- Fabric produced from yarn versus fabric purchased or otherwise sourced.
- Existing fabric stock availability.
- Remaining stock after reservation and consumption.
- Unit conversions and material requirement calculations.
- Material reservation without double-counting available stock.

For example, the front and back of a shirt may use different fabric weights or compositions. Their requirements must be calculated independently.

Separate theoretical requirements, reserved quantities, actual issued quantities, and actual consumption.

Use the existing consumption calculation if correct; document and test any necessary changes.

**Acceptance criteria:** Fabric requirements are calculated from size-wise production quantities and size-wise consumption, with wastage, colour, part, stock, and unit conversions applied correctly.

## Phase 3 — Yarn Planning

Reuse the existing Yarn Master and yarn inventory.

The screenshots show yarn planning with counts, yarn names, colours, and consumption percentages.

Implement:

- Yarn assignment to applicable fabric/body-part combinations.
- Yarn composition percentages.
- Yarn colour and count.
- Consumption percentages.
- Required yarn calculation.
- Yarn stock, reserved quantity, and shortage.
- Yarn planning templates where supported.
- Clear identification of fabric produced from yarn versus fabric requiring no yarn planning.

Yarn planning must be optional for production lots and styles that do not require it.

If the fabric is already available as finished fabric, do not generate an unnecessary yarn requirement.

For blended yarn, validate the composition percentages according to the configured business rules.

**Acceptance criteria:** Yarn requirements are generated only for applicable fabric, with correct composition and stock calculations.

## Phase 4 — Trims and Packing Materials Planning

Reuse the existing Trims and Packing Materials masters.

Follow the screenshots' Trims Planning structure, including UOM, trims category, trims type, quantity per piece, wastage, size-wise factors, templates, and colour assignment.

Implement:

- Trims linked to style parts and styles.
- Separate trims colour assignment.
- Size-specific trims consumption.
- Sizeable and non-sizeable trims.
- UOM conversion.
- Wastage percentages.
- Quantity-per-piece or configurable factor calculations.
- Templates where supported.
- Packing materials, including carton boxes, size labels, and other applicable items.
- Stock availability and shortages.
- Actual material issue and consumption tracking.

A collar may use a different trim than the shirt front. A trouser may use different trims for its waistband, fly, pockets, and belt loops.

Support different trims and quantities by part, colour, and size where applicable.

Packing material quantities must be driven by the actual packing configuration, not blindly multiplied by garment quantity.

**Acceptance criteria:** Each part receives only its applicable trims and accessories, with correct colour, size, quantity, wastage, and UOM calculations.

## Phase 5 — Life Cycle, Process Routing and Tolerance

Reuse the existing Process Master and lifecycle or routing functionality.

The screenshots include process selection, tolerance percentage, life cycle templates, and total tolerance.

Support configurable processes such as:

Knitting → Dyeing → Compacting → Cutting → Stitching → Checking → Ironing → Packing.

This is an example route, not a mandatory sequence for every style.

Implement:

- Configurable process routing by style or style part.
- Process dropdowns backed by the existing Process Master.
- Inline creation of process names where permitted.
- Reusable routing templates.
- Stage sequence and dependencies.
- Applicable tolerance percentages.
- Per-process tolerance and total tolerance summary.
- Validation of incoming, processed, accepted, rejected, and pending quantities.
- Audit history for tolerance overrides.

Do not blindly add all tolerance percentages to the production quantity. Define the calculation according to the relevant business rule and distinguish expected yield loss from excess production allowance.

Tolerance must not permit more output than the available input without an explicit, recorded adjustment.

**Acceptance criteria:** Each style part follows its configured route, and tolerance affects planning or variance calculations only according to the defined rules.

## Phase 6 — BOM and Material Requirement Consolidation

Implement or extend the existing Bill of Materials.

The screenshots show separate sections for Yarn Required, Fabric Required, and Trims & Accessories Required.

Generate BOM requirements from the approved planning data.

For each item, display:

- Material or SKU name.
- Applicable style, part, colour, and size where relevant.
- UOM.
- Required quantity.
- Available stock.
- Reserved quantity.
- Shortage.
- Final planned quantity.
- Budget rate and estimated cost where supported.
- Purchase order and inward status where applicable.
- Approval status.

Implement material-level and order-level totals.

Do not treat planned requirements as actual stock consumption.

Prevent duplicate BOM generation and provide a safe regeneration mechanism when source planning changes.

Reconcile the BOM against fabric, yarn, trims, and packing material requirements. Do not count the same physical material twice because it appears at multiple planning levels.

**Acceptance criteria:** An order's BOM is traceable to its style parts, size quantities, colours, consumption assumptions, and applicable process route.

## Phase 7 — Wages and Other Expenses

Reuse the existing wage, operation, process, and expense functionality.

Follow the screenshot's Wages structure where relevant:

- Order and order number.
- Style name.
- Process name.
- Operation.
- Rate and maximum rate.
- Wage templates.
- Other expenses.
- Production quantity and order value summaries.

Support applicable rates by style part, process, operation, and production quantity.

Keep estimated costs separate from actual costs.

Ensure that the quantity used for a wage calculation follows the relevant process and size/part configuration. Do not use a single overall order quantity for every operation without verifying the applicable costing rule.

**Acceptance criteria:** Production costs are attributable to the relevant order, style, part, process, and operation, with consistent totals and no duplicate charges.

## Phase 8 — Production Lot Creation and Material Issue

Implement the production lot workflow using the approved order, style-part, size, colour, BOM, and routing data.

A lot must retain a snapshot of the planning values at the time of creation while preserving links to the original masters.

Support:

- Production lot number and order reference.
- Style, part, colour, size, and quantities.
- Applicable material allocations.
- Input material weights and quantities.
- Material issue and receipt records.
- Process-specific input and output.
- Actual consumption.
- Partial material availability.
- Shortage warnings.
- Lot splitting and merging only where business rules permit.
- Lot-level costing and traceability.

Do not allow stock to be issued twice through duplicate requests or retries.

Stock movements must be transactional and auditable.

## Phase 9 — Cutting, Checking, Packing and Completed

Implement the four primary stage-specific production pages.

### Cutting

Support weight-based cutting and size-wise output.

Example:

- Input fabric: 100 kg.
- Fabric incorporated into cut panels: 80 kg.
- Remainder: 20 kg.
- Of the 80 kg, track any subsequent classification into accepted panels, wastage, or other outcomes.

Record:

- Input weight.
- Output weight.
- Size-wise cut quantity.
- Part and colour.
- Average weight per piece.
- Expected and actual consumption.
- Process tolerance.
- Usable remainder.
- Wastage.
- Reusable or resale material.
- Operator and timestamps.

The example is illustrative. Never assume that the full 20 kg remainder is wastage.

Use a configurable rule to classify material as reusable return, resale, scrap, or wastage.

Example calculation:

If 80 kg of fabric is converted into 160 pieces, average fabric weight per piece is 0.5 kg. The application must calculate this from actual recorded weights and output quantities.

Support the configured cutting allowance, including the requested 3% default where applicable, but make it configurable and show the resulting expected versus actual variance.

If an approved rate is ₹100/kg, a 3% cutting allowance may produce a planning reference of ₹103/kg. Do not automatically add this percentage to every stage or actual cost without an explicit rule.

### Checking

Receive only quantities released from Cutting.

Record size-wise:

- Incoming quantity.
- Checked quantity.
- Accepted quantity.
- Rejected quantity.
- Rework quantity.
- Pending quantity.
- Defect reason.
- Rework or rejection disposition.

Do not send rejected items directly to Packing unless the configured workflow explicitly permits it.

### Packing

Receive only quantities cleared for Packing.

Support:

- Size-wise and colour-wise packing quantities.
- Style-part reconciliation where applicable.
- Box count and packing configuration from the Style or Packing Master.
- Partial packing.
- Carton or box identifiers where needed.
- Packing material consumption.
- Packed, pending, damaged, and rejected quantities.
- Packing completion timestamp.

Do not assume one box equals one garment. Use the configured packing ratio or packing rules.

### Completed (Consolidated)

Provide a consolidated view of completed production across the order and its lots.

Show:

- Ordered quantity.
- Planned quantity.
- Cut quantity.
- Checked quantity.
- Accepted quantity.
- Packed quantity.
- Remaining quantity.
- Rejected quantity.
- Rework quantity.
- Variance and tolerance.
- Lot-level drill-down.
- Style-part, colour, and size breakdown.
- Finished goods inventory status.

All figures must derive from stage transactions rather than manually maintained totals.

## Phase 10 — Delivery Challan, Returns, Inventory and GST

Extend the existing inventory, dispatch, and document functionality.

### Delivery Challan

Generate a Delivery Challan (DC) when an actual outward movement is recorded.

The user should be able to create it at the time of outward movement, as required by the existing business process.

Implement:

- DC number and date.
- Source and destination.
- Material or product details.
- Lot and inventory references.
- Size, colour, and quantity where applicable.
- UOM and weight.
- Purpose of movement.
- Returnable/non-returnable classification.
- Linked return records.
- Document history and print/export where supported.

Validate against available stock, including partial availability.

For example, if 1,000 units are requested and only 500 are available, the system must show the available 500 and the remaining shortage. It must not silently issue 1,000.

### Returns and remainder

Record returned material independently from usable stock, resale stock, scrap, and wastage.

A return must reference its originating lot or DC where applicable.

Prevent the same remainder from being returned or credited twice.

### GST and HSN

Reuse existing tax and product configuration.

Support HSN/SAC as applicable, GST rates, taxable values, and tax calculations in the relevant documents.

Do not hardcode tax rates or assume the same rate applies to all products.

### Inventory ageing

Calculate inventory days from warehouse receipt or inward date to outward/dispatch date.

Where material remains in stock, calculate age as of the selected reporting date.

Support manual date correction with appropriate permissions and audit history.

AI-assisted extraction of dates from documents may be offered as an optional input method, with user confirmation. Manual entry must remain available.

**Acceptance criteria:** All outward movements and returns reconcile with inventory balances, and inventory ageing is traceable to dated stock transactions.

## Phase 11 — Integration, Reporting, Migration and Testing

Integrate the production workflow with the existing CRM & ERP without breaking unrelated modules.

Implement:

- Order-to-production traceability.
- Material planning versus actual consumption.
- Production progress dashboards.
- Size/colour/part-wise pending quantities.
- Lot-wise yield and wastage.
- Material shortages.
- Process-wise rejection and rework.
- Production costs and variance.
- Inventory ageing.
- Dispatch and DC reconciliation.
- Audit history and permissions.

Test the complete workflow using realistic data for a shirt and a trouser, with multiple style parts, colours, and sizes.

Include cases for:

- Unequal size quantities.
- Different colours by style part.
- Optional yarn planning.
- Multiple fabrics and trims.
- Missing material and partial stock.
- Cutting remainder and wastage.
- Partial stage completion.
- Rejected and reworked pieces.
- Packing ratios and multiple boxes.
- Duplicate requests.
- Invalid stage transitions.
- Tolerance boundaries.
- Existing historical orders and records.

Add backend unit tests, API integration tests, frontend workflow tests where the project supports them, and database migration tests.

Verify that unrelated CRM, purchasing, inventory, and finance functionality remains operational.

---

# 8. Database and API design requirements

Follow the existing repository's conventions. Do not create tables with these names blindly if equivalent entities already exist.

Ensure the data model can represent the following logical entities and relationships:

- Size chart and size values.
- Colour master.
- Style and style part.
- Style-part colour.
- Size-wise order quantities.
- Style-part-specific fabric requirements.
- Size-wise consumption.
- Yarn composition and allocation.
- Trims and packing material requirements.
- Process routing and tolerance.
- BOM and material reservations.
- Production lots.
- Stage transactions.
- Size-wise input and output.
- Quality inspection and rework.
- Material returns and wastage.
- Delivery Challans.
- Packing records and cartons.
- Inventory movements.
- Costing and wage transactions.

Enforce appropriate foreign keys, unique constraints, validation, and indexes.

Use PostgreSQL transactions for related stock and production updates.

Avoid floating-point arithmetic for financial values and weight/quantity calculations where decimal precision is required.

Use the existing API and ORM patterns. Keep business calculations in appropriate backend services rather than duplicating them across frontend components.

Maintain auditability for quantity changes, tolerance overrides, approvals, stock movements, and stage transitions.

---

# 9. User interface requirements

The interface should be clean, consistent, and practical for garment-factory staff.

Use the existing design system.

Follow the reference screenshots' useful layout patterns:

- Step-based planning workflow.
- Clearly separated sections.
- Dense but readable size-wise tables.
- Searchable dropdowns.
- Inline creation where permitted.
- Add/remove rows.
- Reusable templates.
- Colour assignment tables.
- Totals and requirement summaries.
- Clear stock and shortage indicators.
- Confirmation for destructive actions.
- Back, Save, Continue, and Approve actions as appropriate.

Make tables usable on typical desktop screens, with horizontal scrolling when necessary. Keep key identifiers visible and use sticky headers where supported.

Do not show every production stage's work on a single cluttered page.

Each stage page must present only eligible work for that stage, with the ability to drill down into the relevant order, lot, part, colour, and size.

Use clear empty states, validation messages, loading indicators, and save confirmations.

Preserve existing navigation and permissions.

---

# 10. Rules that must never be violated

1. Extend the existing system; do not replace it.
2. Audit before modifying code.
3. Reuse existing masters and entities wherever possible.
4. Implement one phase at a time.
5. Never use only an overall quantity for operational production.
6. Keep size, colour, style part, lot, and stage traceability.
7. Do not make yarn mandatory for every style or lot.
8. Do not add production Input/Output fields to Style Creation.
9. Support custom style-part names without code changes.
10. Do not assume all garment parts share the same colour, fabric, trims, or consumption.
11. Do not show work on a downstream stage before the required upstream transition.
12. Never allow stock to become negative silently.
13. Do not classify every cutting remainder as wastage.
14. Do not confuse planned, reserved, issued, consumed, returned, and available quantities.
15. Do not double-count material requirements or inventory movements.
16. Do not apply tolerance or costing percentages without an explicit, tested business rule.
17. Preserve historical production data and existing application behaviour.
18. Do not use mock data to claim a backend feature is implemented.
19. Do not mark a phase complete until its acceptance criteria and relevant tests pass.
20. Do not proceed to the next phase automatically.

# 11. Required deliverables for every phase

For each phase, report:

1. Scope completed.
2. Existing entities reused.
3. New or modified database entities and migrations.
4. Backend endpoints and business logic changed.
5. Frontend screens and interactions changed.
6. Calculations implemented, including formulas and assumptions.
7. Validation and permissions.
8. Tests executed and their actual results.
9. Known limitations or unresolved business decisions.
10. Updated phase checklist.
11. Files changed and any migration or deployment instructions.

If a requirement is ambiguous, record the ambiguity and identify the safest implementation that preserves traceability. Ask only when a decision materially changes stock, costing, production quantities, or statutory documents.

## Start now

Execute **Phase 0 only**.

Inspect the existing repository and uploaded reference screenshots. Produce the audit and phased implementation plan, identifying what already exists and what must change.

Do not start Phase 1 until the Phase 0 report is complete and presented.

After Phase 0, wait for approval to implement Phase 1. Continue using the same controlled, phase-by-phase process for every subsequent phase.