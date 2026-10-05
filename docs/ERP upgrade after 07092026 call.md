# ERP — Sales, Inventory & Stock Management Add-on Requirements

## Objective

Extend the apparel ERP with a tightly integrated **Sales Order, Inventory, Stock Movement, Packing Slip, Purchase Order, and Stock Adjustment workflow**.

The implementation should follow the existing ERP architecture and master-data principles. Do not introduce duplicate product records or independent stock systems.

---

# 1. Default Pricing

- The system's **default product price should be the Wholesale Price**.
- Wherever a product price is automatically populated for sales transactions, use the configured Wholesale Price as the default.
- Users with appropriate permissions should be able to override the price when required.
- The system should retain the actual transaction price separately from the master/default price.

---

# 2. Sales Order Workflow

Create a complete Sales Order workflow.

### Sales Order Creation

When creating a Sales Order:

1. Select the Customer from the Customer Master.
2. Select Product/SKU from the Product Master.
3. Fetch the available product information automatically.
4. Display current inventory availability.
5. Enter required quantities.
6. Apply the appropriate selling price, defaulting to Wholesale Price.
7. Allow applicable price/order adjustments according to permissions.
8. Save the Sales Order.

### Existing Inventory Check

Before confirming a Sales Order:

- Check the current available inventory for the selected Product/SKU.
- Clearly show:
  - Ordered Quantity
  - Available Stock
  - Quantity already committed/reserved, if applicable
  - Remaining quantity to be fulfilled
- Do not assume that available stock equals total physical stock if some stock is already committed to other orders.

The user should be able to identify whether the order can be fulfilled from existing inventory.

---

# 3. Multiple Sales Orders per Customer

A single customer must be able to have **multiple Sales Orders**.

The data model must therefore be:

```text
Customer
   |
   +-- Sales Order 001
   |
   +-- Sales Order 002
   |
   +-- Sales Order 003
   |
   +-- Sales Order N
```

Do not restrict one customer to one active Sales Order.

Each Sales Order must have its own:

- Order number
- Date
- Customer
- Products/SKUs
- Quantities
- Prices
- Status
- Fulfilment information
- Packing Slip linkage
- Relevant transaction history

---

# 4. Packing Slip

Sales Order fulfilment should support generation of a **Packing Slip**.

Recommended flow:

```text
Customer
   ↓
Sales Order
   ↓
Inventory Availability Check
   ↓
Stock Allocation / Fulfilment
   ↓
Packing Slip
   ↓
Dispatch
```

The Packing Slip should reference the originating Sales Order and customer.

It should contain the relevant:

- Customer details
- Sales Order number
- Product/SKU
- Description
- Quantity
- Packing information
- Dispatch/fulfilment details

---

# 5. Sales Order Against Purchase Order

A Sales Order may be created **against a customer Purchase Order (PO)**.

The system should support PO reference information and validation.

### PO Quantity Tolerance

Allow a configurable **±5% quantity tolerance** against the Purchase Order.

Example:

```text
Customer PO Quantity = 1,000 pcs

Allowed range:
Minimum = 950 pcs
Maximum = 1,050 pcs
```

The system should validate the Sales Order quantity against this tolerance.

The tolerance should be treated as a business rule/configuration rather than hard-coded into unrelated modules.

---

# 6. Stock Balance Filtering

The Inventory / Stock Balance screen should provide useful filtering.

At minimum, support filtering by:

- Product
- SKU
- Product category
- Customer/order context where applicable
- Stock availability/status
- Other existing inventory master dimensions

The important requirement is that users must be able to quickly identify **in-stock balances** rather than manually inspecting the entire inventory.

---

# 7. Automatic Stock-In from GRM

When goods are received through the existing **GRM / Goods Receipt workflow**, the system should automatically update inventory.

Expected flow:

```text
GRM / Goods Receipt
       ↓
Receipt Confirmation
       ↓
Automatic Stock-In
       ↓
Inventory / Stock Balance Updated
```

Users should not have to manually create a separate stock-in transaction for the same confirmed receipt.

The stock transaction should retain its source/reference to the GRM document.

---

# 8. Stock Adjustment

Create a unified Stock Adjustment functionality.

The user specifically requires the ability to:

- Add stock
- Reduce stock
- Replace stock

These should be handled through **one Stock Adjustment workflow**, rather than separate disconnected screens.

### Adjustment Types

```text
Stock Adjustment
├── Add
├── Reduce
└── Replace
```

Each adjustment should capture:

- Product/SKU
- Existing quantity
- Adjustment type
- Adjustment quantity
- Resulting quantity
- Reason
- Date/time
- User/account responsible
- Reference/document where applicable

Stock adjustments must create proper inventory transaction records.

---

# 9. Adjustment / Transfer

Inventory movement should distinguish between:

### Stock Adjustment

Used when correcting or changing the stock balance.

```text
Adjustment
→ Add
→ Reduce
→ Replace
```

### Stock Transfer

Used when moving stock from one inventory location/bin/warehouse/context to another.

```text
Location A
     ↓
Stock Transfer
     ↓
Location B
```

Do not treat a transfer as an unexplained stock reduction followed by an unrelated stock addition.

Both sides of the movement should remain traceable.

---

# 10. Merge Products & Stock Balance

The system should support **merging products**, including their associated stock balances, when products are identified as duplicates or need to be consolidated.

The merge operation must be controlled and auditable.

Conceptually:

```text
Product A
Stock A
   \
    → MERGE → Master Product
   /
Product B
Stock B
```

After merging:

- The resulting product/SKU relationship must remain valid.
- Applicable stock balances should be consolidated.
- Historical transactions should not be silently deleted.
- Previous product references should remain traceable where required.
- The system should prevent accidental duplicate stock creation during the merge.

This should be treated as a controlled administrative operation.

---

# 11. Stock Value Visibility

Stock **quantity** can be visible according to normal inventory permissions.

However:

> **Stock Value should be visible only to Admin users.**

Non-admin users should not be able to see the monetary valuation of inventory unless explicitly granted permission.

Implement this as a role/permission rule rather than merely hiding the UI element.

Example:

```text
ADMIN
├── Stock Quantity       ✓
├── Stock Balance        ✓
└── Stock Value          ✓

NON-ADMIN
├── Stock Quantity       ✓
├── Stock Balance        ✓
└── Stock Value          ✕
```

---

# 12. Account Name in Transaction Log

Every relevant inventory/financial transaction log entry should identify the **account/user responsible for the transaction**.

Transaction history should capture, where applicable:

- Account/User name
- Transaction type
- Product/SKU
- Quantity
- Previous balance
- New balance
- Date/time
- Reference document
- Reason
- Source module

Example:

```text
Stock Adjustment
Product: ABC-001
Type: Reduce
Quantity: 20 pcs
Previous Stock: 500 pcs
New Stock: 480 pcs
Reason: Physical stock correction
Account: John
Date: 02-Oct-2026
```

The transaction log should be immutable/auditable rather than allowing users to silently rewrite historical movements.

---

# 13. Unified Inventory Principle

All inventory changes must flow through a common stock ledger.

The system should avoid independent stock balances maintained separately by different modules.

Conceptually:

```text
                    ┌── GRM / Goods Receipt
                    │
                    ├── Production Output
                    │
                    ├── Stock Adjustment
                    │
                    ├── Stock Transfer
                    │
                    ├── Sales Fulfilment
                    │
                    └── Other approved stock movements
                              │
                              ↓
                       STOCK LEDGER
                              │
                              ↓
                       STOCK BALANCE
```

Every movement should have a source and transaction history.

---

# 14. Overall Sales + Inventory Flow

The high-level workflow should support:

```text
PRODUCT / SKU MASTER
        │
        ├───────────────┐
        │               │
        ↓               ↓
     GRM / PO       EXISTING STOCK
        │               │
        ↓               │
 AUTOMATIC STOCK-IN     │
        │               │
        └───────┬───────┘
                ↓
          STOCK BALANCE
                │
                ↓
          SALES ORDER
                │
        INVENTORY CHECK
                │
                ↓
        STOCK ALLOCATION
                │
                ↓
          PACKING SLIP
                │
                ↓
             DISPATCH
```

Separately:

```text
STOCK BALANCE
      │
      ├── Adjustment → Add / Reduce / Replace
      │
      └── Transfer → Location A → Location B
```

---

# 15. Important Implementation Rules

### Product/SKU Source of Truth

Always use the existing Product/SKU Master.

Do not create duplicate product definitions inside Sales Order, Inventory, Packing Slip, or Stock Adjustment modules.

### Stock Source of Truth

All stock balances must ultimately be derived from the inventory transaction/stock ledger.

Do not maintain independent manually editable stock numbers in individual modules.

### Traceability

Every stock movement should be traceable to its source:

```text
GRM
Sales Order
Packing Slip
Production
Adjustment
Transfer
Other approved source
```

### Permissions

Sensitive information such as **stock valuation** must be controlled through role-based permissions.

### Auditability

Inventory-changing operations must create transaction logs containing the responsible account/user.

### Historical Data

Merging products or adjusting stock must not destroy the historical transaction trail.

---

# 16. Claude Implementation Guardrail

**IMPORTANT — DO NOT SIMPLIFY THESE REQUIREMENTS AWAY.**

When implementing these features:

1. Use existing Product/SKU Masters.
2. Use existing Customer/Supplier Masters.
3. Do not create duplicate product/customer/supplier records.
4. Do not create independent stock systems for Sales, GRM, Production, or Adjustments.
5. All stock changes must update the common inventory ledger.
6. GRM confirmation must automatically create the corresponding stock-in.
7. Sales Orders must check existing available inventory.
8. One Customer can have multiple Sales Orders.
9. Sales Orders can reference customer POs.
10. PO quantity tolerance must support ±5%.
11. Packing Slips must remain linked to their Sales Orders.
12. Stock Adjustment must support Add, Reduce, and Replace in one workflow.
13. Stock Transfer must remain distinguishable from Stock Adjustment.
14. Product merging must preserve historical transaction traceability.
15. Stock Value visibility must be Admin-only.
16. Transaction logs must record the responsible Account/User.
17. Do not silently change existing Style Master, LOT, production, costing, or inventory business rules while implementing these features.
18. Before changing an existing business rule, explicitly identify the conflict and obtain business approval.

---

## Business Intent

The goal is to create a connected ERP rather than isolated modules:

**Masters → Procurement/GRM → Inventory → Sales Order → Fulfilment → Packing Slip → Dispatch → Transaction Ledger**

with every quantity and stock movement remaining traceable, auditable, and linked to the appropriate Product/SKU and business document.

Upgrade #2

# Garment ERP — Style Creation, Production Lot & Inventory Enhancements

## Objective

Implement the following enhancements to the Garment ERP without breaking the existing workflow.

The system must treat **Style Master / Style Creation as the source of truth** for production configuration. Production Lots should fetch the relevant Style Master data automatically and use it to execute production, calculate consumption/costs, track inventory and generate stock/document transactions.

Do not introduce unnecessary input/output fields inside Style Creation where explicitly stated below.

---

# 1. MASTER DATA

## 1.1 Size Chart Master

Create/configure a Size Chart Master.

Each size chart must allow:

- Size name/code
- Quantity applicable for each size
- Multiple sizes within one size chart
- Size-wise consumption where applicable

Example:

```text
Size Chart: T-Shirt Standard

S   → Quantity / configuration
M   → Quantity / configuration
L   → Quantity / configuration
XL  → Quantity / configuration
XXL → Quantity / configuration
```

The quantity for each size must be configurable and reusable from Style Creation.

---

## 1.2 Colour Master

Create a separate Colour Master.

Each colour should have:

- Colour name
- Colour code/SKU component
- Active/inactive status

Styles and inventory should always use the Colour Master rather than free-text colours wherever possible.

---

## 1.3 Process Master

Process names should be selectable through a dropdown.

The system should support processes such as:

- Knitting
- Dyeing
- Compacting
- Printing
- Cutting
- Making
- Fusing
- Stitching
- Trimming
- Checking
- Ironing
- Packing

Processes should be configurable rather than hard-coded.

Each process can have its own:

- Rate
- Unit
- Tolerance %
- Minimum rate
- Maximum rate
- Supplier/worker/agent where applicable
- Insourcing/outsourcing configuration

---

# 2. PRODUCT SKU RULE

## Always use Product SKU

All production, inventory, stock movement and transaction references must ultimately map back to a **Product SKU**.

Do not create disconnected product records for individual transactions.

---

# 3. STYLE CREATION

Style Creation is the **master configuration** from which Production Lots should later fetch their production requirements.

## 3.1 Style Creation should contain

- Style Name
- Style SKU
- Product
- Product parts
- Size Chart
- Sizes
- Colours
- Fabric configuration
- Fabric consumption
- Size-wise consumption
- Trims
- Packing materials
- Production processes
- Process sequence
- Process rates
- Process tolerance %
- Default/previously declared units
- Default prices/rates
- GST/HSN configuration where applicable
- Packing configuration

---

## 3.2 Style SKU

Style SKU should support different parts.

Required SKU structure:

```text
SKU - Size - Colour
```

Example:

```text
TSHIRT01-M-BLACK
TSHIRT01-L-BLACK
TSHIRT01-XL-WHITE
```

If a product has multiple parts, each part may have its own style name/code.

Example:

```text
T-Shirt
 ├── Body
 ├── Sleeve
 └── Collar
```

Different style names/codes may be maintained for different parts where required.

---

## 3.3 Clone Style

Provide:

**Clone Style**

The user should be able to:

1. Select an existing Style.
2. Clone it.
3. Create a new Style from the cloned configuration.
4. Edit only the required fields.
5. Save it as a new Style.

The original Style must not be modified.

---

## 3.4 Previously Declared Values

When editing or creating a Style based on an existing configuration:

Previously declared:

- Units
- Prices
- Rates
- Consumption
- Processes
- Trims
- Packing materials
- Size configuration
- Colour configuration
- Other relevant master values

should be automatically pre-populated.

The user should not have to repeatedly enter the same information.

---

# 4. FABRIC STYLE CREATION

Fabric configuration should be simple.

Fabric should be defined using relevant attributes such as:

- Yarn
- Count
- Knit/Fabric type
- Colour
- GSM
- Dia
- Fabric specification
- Consumption

### Important

**Feeder must be changed to GSM.**

Do not use Feeder as the primary field for this configuration.

---

## Yarn

Yarn should be optional in Production Lot creation.

There should be **no mandatory Yarn requirement in a Production Lot**.

Yarn can remain part of Style/Fabric configuration when relevant.

Example:

```text
30s VL
30s RL
40s VL
40s RL
```

---

# 5. FABRIC → GARMENT FLOW

The system should support the overall flow:

```text
Yarn
 ↓
Fabric
 ↓
Knitting
 ↓
Dyeing
 ↓
Compacting
 ↓
Fabric Stock
 ↓
Cutting
 ↓
Making
 ↓
Trimming
 ↓
Checking
 ↓
Ironing
 ↓
Packing
 ↓
Finished Goods
```

Not every style must necessarily use every process.

The Style Master determines which processes apply.

---

# 6. FABRIC INVENTORY

Fabric stock must be tracked separately from garment stock.

Support:

- Fabric receipt
- Fabric issue
- Fabric return
- Excess delivery
- Colour-wise stock
- Weight-wise stock
- Remaining stock
- Stock valuation

### Excess delivery

If a fabric supplier delivers more quantity/weight than planned, the excess must be recorded rather than silently ignored.

Example:

```text
Planned fabric: 100 kg
Received: 105 kg

Excess: 5 kg
```

The system should retain this information in inventory.

---

# 7. PRODUCTION LOT

Production Lot must fetch its configuration from the selected Style Master.

Example:

```text
Style Master
     ↓
Create Production Lot
     ↓
Automatically fetch Style configuration
     ↓
Execute production
     ↓
Record actual quantities
     ↓
Calculate variance / wastage / gain / loss
```

The user should not have to recreate the complete process configuration for every Lot.

---

# 8. LOT SIZE

The system should support the business rule:

```text
1 Lot = 500 kg
```

Example:

```text
500 kg
= 100 kg × 5 lots
```

These lots may represent different colours.

Example:

```text
Lot 1 → 100 kg → Black
Lot 2 → 100 kg → White
Lot 3 → 100 kg → Blue
Lot 4 → 100 kg → Red
Lot 5 → 100 kg → Green
```

The system must support splitting a larger production requirement into multiple lots.

---

# 9. WEIGHT-BASED CUTTING

Cutting must support weight-based production.

Example:

```text
Input Fabric = 100 kg

Cutting Output:
80 kg converted into garment pieces

Remaining:
20 kg
```

The system must calculate:

- Input weight
- Output weight
- Number of pieces
- Weight per piece
- Remaining weight
- Wastage
- Resale/recoverable material where applicable

Example:

```text
Input = 100 kg
Cut panels = 65 kg
Remaining = 35 kg

Of remaining:
15 kg → Wastage
20 kg → Return / Resale / Recoverable stock
```

The exact classification should be recorded rather than losing the balance.

---

# 10. PIECE ↔ KG CONVERSION

Support conversion between weight and pieces.

Example:

```text
1 piece = 500 g

Therefore:

1 kg = 2 pieces
```

If the rate is:

```text
₹100 per 500 g
```

then the equivalent rate can be calculated as:

```text
₹200 per kg
```

The system should support such conversions automatically where the relevant unit conversion is configured.

---

# 11. PROCESS TOLERANCE

Each Production Process must support a configurable tolerance percentage.

General default:

```text
Wastage Tolerance = 3%
```

This should be configurable at Style/Process level and should not be hard-coded permanently.

Example:

```text
Cutting input = 100 kg
Tolerance = 3%

Permitted tolerance = 3 kg
```

The system should distinguish between:

- Within tolerance
- Above tolerance
- Below expected output
- Actual gain/loss

---

# 12. GAIN / LOSS

Production Lots must calculate gain/loss at:

- Lot level
- Weight level
- Process level
- Quantity level where applicable

Example:

```text
Input = 100 kg
Expected output = 97 kg
Actual output = 95 kg

Variance = -2 kg
```

The system should clearly show whether the variance is within the configured tolerance.

---

# 13. MAKING PROCESS

Making can contain multiple sub-processes.

Example:

```text
Making
 ├── Fusing
 ├── Stitching
 ├── Trimming
 └── Checking
```

Different styles may have different Making stages.

The Style Master should define the applicable sequence.

---

# 14. MAKING STOCK VALIDATION

For every Making stage:

**OUT quantity must never be greater than available IN quantity.**

Rule:

```text
OUT ≤ IN
```

Example:

```text
IN = 500 pcs
OUT = 500 pcs → Allowed

IN = 500 pcs
OUT = 501 pcs → Not allowed
```

The system must prevent negative or impossible production balances.

---

# 15. INSOURCING & OUTSOURCING

Every applicable production process should support:

- In-house / Insourcing
- Outsourcing

For outsourcing:

- Supplier must be selected from Supplier Master.
- Delivery Challan should be generated for outward movement.
- Received quantity must be recorded when material returns.
- Supplier/process rate must be recorded.
- Difference between OUT and IN must be tracked.

---

# 16. MASTER DATA SOURCING

Supplier and Customer must be maintained separately in Master Data.

Whenever selecting:

- Supplier
- Customer
- Worker
- Agent

the system should fetch the entity from the corresponding master instead of creating duplicate free-text records.

---

# 17. DELIVERY CHALLAN

When material is sent outward for a process/job work:

**Generate Delivery Challan automatically.**

Example:

```text
Lot 15
Process: Fusing
OUT: 100 pcs
Delivery Challan: DC/26-27/015
```

The DC should contain relevant information such as:

- DC Number
- Date
- From
- To
- Product/Style
- Process
- Lot
- Quantity
- HSN where applicable
- Value where applicable

The user should be able to view the generated document.

---

# 18. PARTIAL AVAILABILITY / BALANCE

The system must handle situations where only part of the required quantity is available.

Example:

```text
Required = 1,000 pcs
Available = 500 pcs

Issue:
500 pcs

Remaining:
500 pcs
```

The remaining quantity must remain open/pending and should not be treated as completed.

---

# 19. RETURN REMAINDER

Any unused material remaining after a production process should be returnable to inventory.

Examples:

- Fabric remainder
- Cut panel remainder
- Excess material
- Trims
- Packing materials

The system should record:

```text
Issued
Used
Returned
Wastage
Recoverable/Resale
```

---

# 20. TRIMS

Trims should be configurable in Style Master.

Examples:

- Buttons
- Plastic
- Elastic
- Labels
- Sewing thread
- Stickers
- Other accessories

Each Trim should support appropriate units such as:

- Nos
- Pieces
- Meters
- Kg
- etc.

Trim consumption may be configured at Style/Size level where required.

---

# 21. TRIMS — SIZE-WISE CONSUMPTION

Consumption should support size-wise configuration.

Example:

```text
S  → 4 buttons
M  → 4 buttons
L  → 5 buttons
XL → 5 buttons
```

This should be fetched automatically when the Production Lot is created.

---

# 22. PACKING

Packing configuration should come from the Style Master.

Support:

- Box
- Dozen
- Sets
- Pieces

The final packing/output unit can vary by Style.

Example:

```text
Style A → Pieces
Style B → Dozen
Style C → Sets
Style D → Box
```

---

# 23. BOX COUNT

Box count should be configurable in Style Master.

Production Lot / Packing should automatically fetch the configured box/packing requirement.

Example:

```text
Style:
1 Box = 24 pcs
```

The system should calculate the required number of boxes based on finished quantity.

---

# 24. FIRST QUALITY & REJECTED

Final production output must distinguish:

- First Quality
- Rejected

Example:

```text
Total output = 100 pcs

First Quality = 88 pcs
Rejected = 12 pcs
```

Only **First Quality** pieces should be considered for the final finished-goods selling/production price calculation.

---

# 25. FINAL PRICE

The final price calculation should be based on:

**First Quality finished pieces.**

Rejected pieces should not increase the final selling price calculation in the same way as first-quality pieces.

The system must maintain:

```text
Total production cost
First Quality quantity
Rejected quantity
Cost per First Quality piece
```

---

# 26. TARGET PRICE

Style Master should allow a **Target Price**.

Example:

```text
Calculated Cost = ₹139.41 / pc
Target Price = ₹150 / pc
```

The system should display the comparison.

Target Price should be configurable and editable.

---

# 27. PROCESS RATES

Rates should be configurable for each process.

Examples:

- Knitting rate
- Dyeing rate
- Compacting rate
- Cutting rate
- Fusing rate
- Stitching rate
- Trimming rate
- Checking rate
- Ironing rate
- Packing rate

Rates may be configured based on the applicable unit.

The system should use these rates for planned-vs-actual price comparison.

---

# 28. PLANNED VS ACTUAL COST

Because Style Master contains the planned process configuration and rates, Production Lots should be able to compare:

```text
Planned Cost
vs
Actual Cost
```

At minimum support comparison for:

- Fabric
- Process costs
- Trims
- Packing materials
- Labour/job work
- Additional costs
- Wastage
- Other applicable costs

Show the variance.

---

# 29. ADDITIONAL COSTS

Production Lots must allow additional costs that are not covered by standard process rates.

Example:

```text
Additional Cost = ₹1,000
```

These costs should be included in total lot cost and final cost calculation.

---

# 30. DYEING / PRINTING WEIGHT VARIANCE

Processes such as dyeing/printing may change material weight.

The system must record actual input and output rather than assuming weight remains identical.

Example:

```text
Input = 100 kg
After process = 103 kg
```

The system should show the resulting gain/loss/variance.

Do not automatically classify every weight increase as wastage.

---

# 31. NO PRICE / ERROR / DEFAULT VALUE

If a required rate/price is missing:

- Do not silently calculate an incorrect value.
- Show a clear warning.
- Identify the missing rate.
- Allow an appropriate default value where configured.
- Flag the record for correction.

Example:

```text
⚠ Dyeing rate not configured.
Please configure the rate or use the default rate.
```

---

# 32. BILL / INVOICE ALERTS

If an outsourced process has material sent out but the expected bill/invoice is not received within the configured number of days:

Show an alert/reminder.

Examples:

```text
Bill not received
Invoice not received
Pending supplier document
```

The number of days should be configurable.

---

# 33. FABRIC-FIRST PRODUCTION

The production workflow should support:

```text
Fabric
 ↓
Garment
```

Fabric-related production/inventory must be handled before garment production where applicable.

The system should not force garment production to begin without the required fabric stock/configuration.

---

# 34. GST & HSN

Relevant Products/Styles should support:

- GST rate
- HSN code

These values should be available for applicable transactions/documents such as Delivery Challans and inventory/sales documents.

---

# 35. INVENTORY AGEING

Track inventory ageing from:

**Product entry date into warehouse → Date it leaves warehouse**

Display:

```text
Inventory Age = Exit Date - Warehouse Entry Date
```

If still in stock:

```text
Inventory Age = Current Date - Warehouse Entry Date
```

The system may support:

- Manual date entry
- AI-assisted reading/extraction where applicable

But the actual stored dates must remain explicit and auditable.

---

# 36. STYLE → LOT DATA FLOW

This is the most important relationship.

The flow must be:

```text
MASTER DATA
    ↓
STYLE MASTER
    ↓
PRODUCTION LOT
    ↓
PROCESS EXECUTION
    ↓
STOCK MOVEMENTS
    ↓
COST CALCULATION
    ↓
QUALITY OUTPUT
    ↓
PACKING
    ↓
FINISHED GOODS INVENTORY
```

Production Lot creation should automatically fetch applicable Style Master configuration including:

- Product SKU
- Style
- Parts
- Sizes
- Colours
- Fabric
- Consumption
- Processes
- Process sequence
- Tolerance %
- Rates
- Trims
- Packing
- Box configuration
- GST/HSN
- Target price

The user should then enter **actual production data**, rather than recreating the Style configuration.

---

# 37. IMPORTANT DESIGN PRINCIPLES

1. **Style Master is the source of truth for planned production configuration.**

2. **Production Lot is the execution layer.**

3. **Inventory is updated from actual transactions, not merely from planned Style data.**

4. **Always use Product SKU for product/stock identification.**

5. **OUT quantity can never exceed available IN quantity.**

6. **Support both weight-based and piece-based production.**

7. **Support conversion between units where conversion is configured.**

8. **Track gain, loss, wastage, return and recoverable/resale material separately.**

9. **3% is the general default wastage tolerance, but tolerance must be configurable.**

10. **First Quality and Rejected quantities must be tracked separately.**

11. **Final finished-piece price calculation should use First Quality quantity.**

12. **Supplier/Customer must always come from Master Data.**

13. **Outsourced processes must support Delivery Challans and subsequent inward/receipt transactions.**

14. **Rates and prices should be reusable and automatically populated from previously configured Styles/Masters wherever applicable.**

15. **Missing prices/rates must generate warnings rather than silently producing incorrect calculations.**

16. **Do not force Yarn into Production Lot creation; Yarn is optional.**

17. **Do not add unnecessary Input/Output fields to Style Creation. Actual Input/Output belongs to Production Lot execution.**

18. **Do not hard-code the production process sequence; Style Master determines applicable processes.**

19. **Do not duplicate master data inside individual Lots. Fetch/reference the master records and preserve the configuration snapshot required for historical accuracy.**

20. **Every stock movement must remain auditable.**

---

# 38. REFERENCE EXAMPLE

Example Style:

```text
Style Name: SK-203-50

Product:
T-Shirt

Size:
S / M / L / XL

Colour:
Black / White / Blue

Fabric:
30s VL - S/J - Pink - 30
40s RL - S/J - White - 16

Trims:
Button - 12mm - White
Button - 10mm - Brown
Elastic - 35mm - Lycra
Elastic - 20mm - 3 Weft

Packing:
Inner Card - 7.5" × 11"
BOPP - 8.5" × 11" + 2
Gaset - 5 × 9.25 × 2.75 + flap 1.75
Carton - 24" × 18" × 14"
```

This Style becomes the configuration from which Production Lots are created.

---

# 39. IMPLEMENTATION EXPECTATION

Before changing existing functionality:

1. Inspect the existing Style Creation implementation.
2. Inspect existing Product/SKU, Inventory, Production Lot, Process, Supplier and Customer models.
3. Reuse existing master data wherever possible.
4. Do not create duplicate concepts.
5. Preserve existing working functionality.
6. Implement the above as an extension to the existing ERP architecture.
7. Ensure Style → Lot → Process → Inventory relationships remain consistent.
8. Ensure historical Lots do not unexpectedly change when the Style Master is edited later.
9. Add validation and clear error/warning states.
10. Keep the UI consistent with the existing Kamna-inspired workflow.

The objective is to make the system behave like a real garment manufacturing ERP where **Style Creation defines what should happen, Production Lots record what actually happened, and Inventory/Costing reflect the actual transactions.**