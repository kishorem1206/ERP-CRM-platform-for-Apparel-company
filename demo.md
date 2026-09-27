# Client Demo Script — Apparel Manufacturing CRM/ERP

A rehearsed walkthrough for showing progress to the client. Follow the acts in order — each one builds on the previous, so the story is: **raw material comes in → gets turned into garments on the floor → gets sold and invoiced → everything is tracked, costed, and reported on the way**. Total run time: ~25–35 minutes at a comfortable pace, or ~15 if you skip the optional beats marked *(optional)*.

**Login:** `admin@company.com` / `Kishore@6` at `http://localhost`

---

## Before you start

- Make sure the stack is up (`docker compose ps` — all healthy) and you've done one full login already so the first click isn't slow.
- Open the sidebar once and just glance at the module list (Dashboard, CRM, Sales, Purchasing, Inventory, Production, Finance, Reports, AI Assistant, Security, Admin) — say out loud: *"This is one system — everything you're about to see shares the same database, the same stock ledger, and the same customer/lead records. Nothing here is a bolted-on plugin."*
- Have 2–3 tabs ready if you want to jump around without losing your place: Dashboard, Production, CRM.

---

## Act 1 — The Dashboard (30 seconds)

Land on `/dashboard`.

- Point at the **Manufacturing Pipeline** strip (Yarn → Fabric → Knitting → Production → QC & Pack → Dispatch) — *"This is a live view of where every unit of stock and every lot currently sits, not a static diagram."*
- Point at the Revenue/Receivable/Payable numbers top-right and the Revenue vs Purchase chart — *"These are computed from real transactions, not manually entered."*
- Mention the **"Today's Activities"** popup (bottom-right, if anything's scheduled today) — *"The system also reminds whoever's logged in about their CRM tasks for the day, right from the moment they open the app."*

---

## Act 2 — The Style Master (the foundation) (3–4 minutes)

This is the concept everything else hangs off, so it goes first.

Go to `/production/styles`.

- *"Before we ever cut fabric, we define a Style — think of it as the production blueprint for a garment. It's not just a name and a picture."*
- Open an existing style (or create one live at `/production/styles/new`) and walk through the sections:
  1. **Basic Info** — name, code, garment type, final output unit (Pieces/Dozen/Sets/Boxes — *"not every garment ships by the piece"*).
  2. **Sizes & Colours** — the size chart and colour range for this style, which together define the SKU matrix.
  3. **Yarn & Fabric Requirements** — linked to the actual material masters, not free-typed text.
  4. **Production Workflow** — *this is the standout part* — an ordered, fully configurable list of processes (Cutting, Fusing, Stitching, Ironing, Packing…). For each process you can set:
     - its own **tolerance %** (Cutting might allow 2%, Stitching 3% — not one blanket number for the whole factory)
     - its own **input/output unit** and a **conversion rule** (Cutting outputs pieces even if the style's final packing unit is Dozens)
     - **min / max / planned rate** for costing
     - **sub-processes** (e.g. Stitching → Power Table / Snitex / Helpers)
  5. **Trim & Packing Material Planning** — same master-reference pattern.
- *"None of this is hard-coded. A shirt style and a jacket style can have completely different workflows, and you define that once, here."*

---

## Act 3 — Adding Lots (raw material intake) (3 minutes)

Go to `/inventory/lots` first — *"this is every batch of yarn, fabric, and trim currently on record."* Point out the type filter and the trim sub-filter (Button/Zipper/Elastic/etc., built from real data, not a fixed list).

Now show it getting created. Use the purple **+ Create** button in the sidebar → **Add Yarn** (or Fabric, or Trims):

- Fill a yarn lot: count, ply, mill, composition (fibre % blend), bags × kg/bag auto-calculating total weight.
- Tick the **"Book to Inventory"** section — warehouse, product, unit — *"this is the moment the stock ledger actually moves."*
- Save, then jump back to `/inventory/lots` and show the new lot with its live stock quantity.

*Talking point:* *"Every single stock movement in this system — receipt, issue, transfer, adjustment — is one row in an immutable ledger. There's no 'current stock' number anyone can just edit; the balance is always the sum of the ledger. That's what makes the ageing report and the traceability chain later actually trustworthy."*

*(optional)* Show `/purchase/orders` → `/purchase/grn` briefly to mention that formal purchase orders and goods-receipt also feed the exact same ledger — the quick-add path you just used is for fast/informal intake, the PO→GRN path is for accountable procurement with a vendor and GST.

---

## Act 4 — Production: creating a lot, cutting, knitting, closing (6–8 minutes)

This is the centerpiece. Go to `/production/lots` → **New Lot**.

- Pick the Style you showed in Act 2. Enter planned quantity and size-wise breakdown.
- *"Watch what happens on save."* Open the new lot's detail page and show the **Stages** — they're not a generic Cutting/Making/Finishing/QC/Packing template; they're a direct snapshot of that Style's configured process list, with its tolerance %, units, and rates already carried over.
- *"And this is the important part: if I go back and edit the Style tomorrow, this lot's stages don't change. It's frozen at the moment of creation — that's what lets you compare planned vs. actual honestly, months later, without history rewriting itself."*

**Material Issue (feeding the floor):** go to `/production/mis` → issue yarn/fabric from the warehouse to this lot's first stage. *"This is a real stock deduction — go check `/inventory/transactions` afterward and you'll see the issue logged."*

**Knitting / stage progress:** back on the lot, log stage entries for e.g. Cutting → Knitting/Stitching — input qty, output qty, rejected qty, operator, machine. Advance the lot's status (draft → planned → approved → in_production → qc → packing → ready_to_dispatch).

**Production Output (finished goods):** go to `/production/outputs` → receive the finished quantity into the FG warehouse against this lot. *"This is the reverse of the material issue — stock is now created, not consumed."*

**Closing the lot:** mark it `completed`. *"Once closed, the lot is a permanent, unchangeable record of what actually happened — planned vs actual is now a query, not a spreadsheet reconciliation."*

---

## Act 5 — Price / Cost Calculation (2–3 minutes)

- Open `/reports/production` — planned vs actual efficiency per lot, using exactly the rates you saw baked into the Style/stage in Act 2/4.
- *(optional)* Show the cost-sheet concept if you have a live example — process rate × output quantity, rolled up per lot, compared to the target selling price.
- Talking point: *"Because every rate is attached to a specific process on a specific style, the moment production data is entered, the system already knows what this lot **should** have cost. Actual vs planned isn't a month-end exercise."*

---

## Act 6 — CRM (5–6 minutes)

Switch context: *"Everything so far was 'can we make it.' Now — 'can we sell it.'"*

Go to `/crm/dashboard`.

- **Leads** (`/crm/leads`): show the Kanban pipeline (drag a card between stages) and the list view. Open a lead's detail page — inline-editable fields, linked Person/Organization, activity timeline, notes, email thread.
- **Persons & Organizations**: open a Person, show it auto-links to an Organization — *"select the person, the organization can auto-fill if it's on file."*
- **Activities + Calendar** (`/crm/activities`): show the List view, then flip to **Calendar** — a Teams/Outlook-style month grid with colour-coded call/meeting/task chips, click a day to see details, mark done/undone, edit or delete right from the panel. Point out the **Unscheduled** tray for anything logged without a date.
- **Quotation** (`/crm/quotes`): create a quote from the lead — pick line items from the product catalog, set discount %, see the live subtotal/discount/total footer. Save it, then walk the status flow: Draft → Sent → Accepted.
- *"Once a quote is Accepted, it converts into a formal Sales Order"* — jump to `/sales/orders` (or trigger the convert action) to show the handoff from CRM's pre-sale quoting into the GST-compliant Sales module (`/sales/quotations` → `/sales/orders` → `/sales/deliveries` → `/sales/invoices`).

---

## Act 7 — Reports (2 minutes)

Go to `/reports/stock-ageing`.

- Show the bar chart (stock value by ageing bucket) and the donut chart (% value share) — *"this tells a factory owner in one glance how much money is tied up in stock that hasn't moved in 90+ days."*
- Mention the sibling reports briefly: Sales summary, Purchase summary, GST register (GSTR-1/2A ready), Production efficiency.

---

## Act 8 — AI Assistant *(optional, 2 minutes)*

Go to `/ai-assistant`. Ask something like *"What's my current stock of 40s yarn?"* or *"Show me overdue invoices."*

*"This isn't a chatbot bolted on top — it has live tool access into the actual database. It queries stock, orders, invoices, and production lots in real time and routes the question to the right specialist (inventory, sales, production, finance, purchase) automatically."*

---

## Act 9 — Admin & Security *(optional, 2 minutes)*

`/admin` — users, roles, granular permission editor (grouped by module). `/settings/security` — password change, optional 2FA with QR setup.

*"Every action anyone takes is scoped by role and permission — this isn't one shared login."*

---

## Closing line

*"What you've just seen is one continuous chain: a raw material lot → a Style's blueprint → a production lot that snapshots that blueprint → stage-by-stage floor tracking → finished goods → a CRM lead that became a quote that became that same sales order → an invoice → and every step of it queryable in the reports and traceable end to end. That end-to-end traceability — from a specific fabric lot to the specific customer who received garments made from it — is the query most ERPs can't actually answer. This one can."*

---

## Specialities — what makes this different from an off-the-shelf ERP

Use these as answers when the client asks *"why not just use [Zoho/Odoo/Tally]?"*

1. **Style Master as a true production blueprint, not a product name.** Configurable process workflow per style (not one fixed Cutting→Packing template), per-process tolerance %, per-process input/output units with conversion rules, sub-processes, and planned rate bands — all spec'd out and enforced, not left to spreadsheets.

2. **LOT snapshotting.** A production lot freezes the Style's configuration at the moment it's created. Editing a Style later never rewrites history on lots already in progress or completed — which is what makes planned-vs-actual analysis trustworthy months later.

3. **Immutable ledger-based inventory.** There is no editable "current stock" field anywhere in the system. Every warehouse balance is derived by summing the transaction ledger. This eliminates the single most common source of stock discrepancies in spreadsheet- or basic-ERP-driven factories.

4. **Full material-to-customer traceability.** `inventory_lot → material_issue → production_lot → production_output → inventory_transaction → delivery → invoice → customer` is a real, queryable join chain — "which customers received garments made from fabric lot X?" is answerable today, not a data-archaeology project.

5. **One CRM, one ERP, one database.** Leads, quotes, and customer conversations live in the same system as production and inventory — a sales rep's quote and the factory floor's material issue are one hop apart, not two separate SaaS tools glued together with CSV exports.

6. **Teams-style CRM calendar with an "Unscheduled" safety net.** Built specifically so that logging an activity without a date doesn't make it disappear — most CRMs silently drop undated tasks from calendar views.

7. **Live-data AI assistant, not a canned chatbot.** Specialist agents with direct, permissioned tool access to stock, orders, invoices, and production data — answers reflect what's actually in the database right now.

8. **GST-native from the ground up.** HSN codes, tax rates, GSTR-1/2A register generation, and B2B invoice compliance are core data model concepts, not an add-on module.

9. **Real-time notifications.** Low-stock, overdue-payment, and production-delay alerts are pushed over WebSocket the moment a background job detects them — not discovered by someone opening a report.

10. **Granular, auditable permissions.** Every module has view/create/edit/delete permissions independently assignable per role, down to the level of "can this role delete a CRM lead" vs. "can they only edit it."

11. **Built for apparel specifically**, not adapted from a generic manufacturing template — yarn count/ply/composition, fabric GSM/construction/dia, trim sizable-vs-non-sizable categorization, and size-chart-driven SKU generation are first-class concepts, not custom fields bolted onto a generic "product."
