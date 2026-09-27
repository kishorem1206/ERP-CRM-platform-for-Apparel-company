# Garments ERP --- Style Creation / Style Master Specification

> **STATUS: BASELINE / CRITICAL SYSTEM REQUIREMENT**
>
> This document defines the agreed Style Creation / Style Master concept
> for the garments ERP. Treat this as the **source of truth** for the
> Style Master architecture and workflow. Do **not remove, simplify,
> reinterpret, or change these concepts in future implementation
> iterations** unless the business owner explicitly approves the change.
>
> UI layout, labels, colors, component choices, and technical
> implementation may evolve, but the **business logic and relationships
> defined here must remain intact**.

------------------------------------------------------------------------

## 1. Core Concept

The **Style Master** is the production blueprint/template for a garment
style.

A Style Master defines:

-   Style identity
-   Size and colour variants
-   SKU structure
-   Yarn requirements
-   Fabric requirements
-   Production process/workflow
-   Process/sub-process configuration
-   Process-level tolerance %
-   Input/output units
-   Unit conversions where required
-   Trims requirements
-   Packing-material requirements
-   Planned process rates
-   Other style-specific production rules

A **LOT is an actual production instance of a Style**.

Therefore:

**Style Master = what/how the garment is supposed to be produced**

**LOT = actual execution of that Style**

------------------------------------------------------------------------

# 2. Style Master → LOT Principle

When a LOT is created, the user selects a Style.

The LOT must then fetch/copy the relevant configuration from the Style
Master, including:

-   Style information
-   Applicable sizes
-   Colours
-   SKU/variant information
-   Yarn requirements
-   Fabric requirements
-   Trim requirements
-   Packing-material requirements
-   Production processes
-   Process sequence
-   Sub-processes
-   Tolerances
-   Unit/conversion rules
-   Planned rates

The user should **not have to manually recreate the complete production
workflow for every LOT**.

### Important historical-data rule

A LOT should use a **snapshot/version of the Style Master configuration
at the time the LOT is created**.

Changing the Style Master later must **not retroactively alter an
already-created/running LOT**.

Conceptually:

``` text
STYLE MASTER
     |
     | Create LOT
     v
LOT SNAPSHOT
     |
     v
Actual Production
     |
     v
Planned vs Actual Analysis
```

If the Style Master is changed later, the new configuration applies to
**new LOTs**, not historical LOTs.

------------------------------------------------------------------------

# 3. Example Style Names

The business example includes styles such as:

-   `SK-203-50`
-   `SK-245-50`
-   `IC-2`
-   `IC-338`

A Style is the finished garment/product definition.

------------------------------------------------------------------------

# 4. SKU / Variant Concept

A Style can have multiple combinations of:

-   Size
-   Colour
-   Other applicable variant attributes

The Style Master should support a size chart/size selection and colour
selection.

For example:

  Style    Size   Colour   Example SKU
  -------- ------ -------- ----------------
  MG-300   S      White    MG-300-WHITE-S
  MG-300   S      Black    MG-300-BLACK-S
  MG-300   M      White    MG-300-WHITE-M
  MG-300   M      Black    MG-300-BLACK-M

The exact SKU-generation format can be configurable, but the principle
is:

**Style + applicable variant dimensions = SKU/variant**

------------------------------------------------------------------------

# 5. Separate Master Data

Yarn, Fabric, Trims, and Packing Materials should be maintained as
proper master data rather than repeatedly entered as free text inside
every Style.

Recommended masters:

``` text
Yarn Master
Fabric Master
Trim Master
Packing Material Master
Size Master
Colour Master
Process Master
Unit Master
Rate Master
```

The Style Master **references/selects these master records** and then
defines the style-specific requirements.

This is important for consistency, reporting, inventory, costing, and
future LOT creation.

------------------------------------------------------------------------

# 6. Yarn Master

Example Yarn Master values provided by the business:

-   `30s VL`
-   `30s RL`
-   `40s VL`
-   `40s RL`

A Style can select the yarn(s) applicable to that garment.

The Style-specific Yarn section may additionally define
quantities/consumption, ratios, or other requirements where applicable.

Example:

``` text
Style: SK-203-50

Yarn:
- 30s VL
- 40s RL
```

------------------------------------------------------------------------

# 7. Fabric Master

Fabric is described using attributes such as:

**Count + Knit + Colour + Dia**

Business examples:

-   `30sVL-S/J-Pink-30`
-   `40sRL-S/J-White-16`

These should ideally be records in the Fabric Master.

A Style then selects the applicable fabric and can define its
style-specific consumption/requirement.

Example:

``` text
Fabric:
30sVL-S/J-Pink-30
40sRL-S/J-White-16
```

Potential style-specific data can include:

-   Consumption
-   Quantity
-   Unit
-   Usage
-   Excess %
-   Other production parameters

Do not assume that the encoded fabric name itself is the only data
required; the underlying attributes should remain available where
needed.

------------------------------------------------------------------------

# 8. Trim Master

Business examples:

-   `Button-12mm-White`
-   `Button-10mm-Brown`
-   `Elastic-35mm-Lycra`
-   `Elastic-20mm-3Weft`

Trims should be maintained in the Trim Master.

A Style selects the applicable trim and specifies its requirement.

Example:

  Trim                   Quantity Unit
  -------------------- ---------- ------
  Button-12mm-White             5 Nos
  Elastic-35mm-Lycra         0.65 M

Style-specific trim configuration may include:

-   Required quantity
-   Unit
-   Category
-   Excess %
-   Applicability by size/colour/SKU if required

------------------------------------------------------------------------

# 9. Packing Material Master

Business examples:

-   `InnerCard-7.5"x11`
-   `BOPP-8.5"x11"+2`
-   `Gaset-5*9.25*2.75flap+1.75`
-   `Carton-24"18"14"`

These should be maintained in the Packing Material Master.

The Style then selects the required packing materials and defines the
style-specific usage.

Example:

  Packing Material             Example Requirement
  ---------------------------- ---------------------------
  InnerCard-7.5"x11            1 per applicable unit
  BOPP-8.5"x11"+2              1 per applicable unit
  Gaset-5*9.25*2.75flap+1.75   As defined by style
  Carton-24"18"14"             Based on packing capacity

Packing material planning is part of the Style definition, not an
unrelated standalone feature.

------------------------------------------------------------------------

# 10. Production Workflow

The Style Master must define the production lifecycle/process sequence
for that Style.

Example:

``` text
Cutting
   ↓
Fusing
   ↓
Marking
   ↓
Stitching
   ↓
Trimming & Checking
   ↓
Ironing
   ↓
Packing
```

The exact processes can vary by Style.

The workflow should therefore be **configurable**, not hard-coded for
every garment.

------------------------------------------------------------------------

# 11. Process-Level Configuration

Each process may contain its own configuration.

A process can have:

-   Process name
-   Sequence/order
-   Enabled/disabled status
-   Sub-processes
-   Tolerance %
-   Minimum rate
-   Maximum rate
-   Planned rate
-   Input unit
-   Output unit
-   Conversion rule
-   Applicable machines/operators/sub-processes
-   Other process-specific parameters

Example:

``` text
Stitching
├── Power Table
├── Snitex
├── Helpers
└── Contract %
```

The exact sub-processes may differ by Style/process.

------------------------------------------------------------------------

# 12. Process-Level Tolerance %

A **Tolerance % can be defined separately for each process**.

Example:

``` text
Cutting             → 2%
Stitching            → 3%
Trimming & Checking  → 1%
Ironing              → 2%
Packing              → 1%
```

Tolerance is process-specific.

Do not treat one global tolerance percentage as sufficient for all
processes.

The tolerance can be used to calculate the permissible/expected quantity
range for that process.

Example concept:

``` text
Planned Qty = 1,000
Tolerance = 2%

Expected/allowed range can be derived from the process tolerance.
```

The exact calculation/approval behavior can be finalized during
implementation, but the **ability to configure tolerance per process is
mandatory**.

------------------------------------------------------------------------

# 13. Input and Output Units

Different stages may operate in different units.

For example:

``` text
Cutting       → Pieces
Fusing        → Pieces
Stitching     → Pieces
Ironing       → Pieces
Packing       → Boxes / Dozen / Sets / Pieces
```

The Style Master must therefore support process-specific:

-   Input Unit
-   Output Unit

The system must **not assume that the entire Style always uses one unit
from beginning to end**.

------------------------------------------------------------------------

# 14. Unit Conversion

A process may require conversion between units.

Examples:

``` text
12 Pieces = 1 Dozen
10 Sets   = 1 Box
24 Pieces = 1 Carton
```

The Style Master should allow a conversion rule where required.

Conversion can be:

1.  Defined specifically while creating/configuring a Style, or
2.  Taken from a default/master conversion configuration.

The system should support both the concept of **default conversion** and
**style-specific override** where appropriate.

------------------------------------------------------------------------

# 15. Cutting Output

After Cutting, the production output is fundamentally **pieces**.

The system should understand the material/output transition:

``` text
Cutting
   ↓
Pieces
```

The downstream process can continue with pieces or use another
configured unit/conversion where the business workflow requires it.

------------------------------------------------------------------------

# 16. Final Ironing & Packing Output

At the end of the production workflow, the finished output may be
represented differently depending on the Style.

Possible final output units include:

-   Pieces
-   Dozen
-   Sets
-   Boxes

Therefore the final output unit must be configurable per Style/workflow.

Example:

``` text
Style A → Final Output = Pieces
Style B → Final Output = Dozen
Style C → Final Output = Sets
Style D → Final Output = Boxes
```

------------------------------------------------------------------------

# 17. Trims Planning

Style Creation includes Trim Planning.

Typical trim types:

-   Button
-   Elastic
-   Labels
-   Sewing Thread
-   Stickers
-   Other applicable trims

Each trim should support information such as:

``` text
Trim Type
Item / Master Reference
Quantity
Unit
Category
Excess %
Applicability
```

Example categories from the business discussion:

-   `Sizable`
-   `Non-Sizable`

An **Excess %** can be configured if required.

Example:

``` text
Button → Nos → Sizable
Elastic → Meters → Sizable
Label → Pieces → Non-Sizable
Sewing Thread → Appropriate Unit → Non-Sizable
```

The categorization should remain configurable rather than assuming every
trim follows the same sizing behavior.

------------------------------------------------------------------------

# 18. Packing Material Planning

Packing Material Planning is part of Style Creation.

The Style defines:

-   Which packing materials are required
-   Quantity/consumption
-   Unit
-   Packing relationship/conversion
-   Excess % where required
-   At which stage the material is consumed/issued, if applicable

The business specifically indicated that packing-material planning
exists and that additional options may be needed around **Ironing &
Packing**, including whether the material is used during the process or
at/after the process.

Therefore the system should support configurable timing/stage for
packing-material consumption where required.

------------------------------------------------------------------------

# 19. Rates

Rates should be associated with the Style's production processes.

Example:

  Process       Planned Rate
  ----------- --------------
  Cutting              ₹2.00
  Fusing               ₹1.00
  Stitching           ₹12.00
  Trimming             ₹2.00
  Ironing              ₹3.00
  Packing              ₹2.00

Depending on the business setup, the system may also maintain:

-   Minimum Rate
-   Maximum Rate
-   Planned Rate
-   Rate basis/unit
-   Process/sub-process rate

The Style Master should hold or reference the applicable planned rates.

------------------------------------------------------------------------

# 20. Planned vs Actual Cost / Rate Comparison

One major purpose of this Style Master structure is to enable automatic
planned-vs-actual comparison.

When a LOT is created:

``` text
Style Master
    ↓
Planned processes
    ↓
Planned rates
    ↓
LOT
```

When actual production data is entered:

``` text
LOT
    ↓
Actual quantity
Actual process
Actual rate
Actual output
Actual consumption
    ↓
Compare against Style/LOT planned values
```

This enables:

-   Planned quantity vs Actual quantity
-   Planned rate vs Actual rate
-   Planned cost vs Actual cost
-   Process-wise variance
-   Style-wise variance
-   LOT-wise variance
-   Efficiency/cost analysis

The Style Master therefore acts as the **baseline for production costing
and performance comparison**.

------------------------------------------------------------------------

# 21. Recommended Overall Data Structure

Conceptually:

``` text
STYLE MASTER
│
├── Basic Information
│   ├── Style Name / Code
│   ├── Product
│   └── Other attributes
│
├── Variants
│   ├── Sizes
│   ├── Colours
│   └── SKUs
│
├── Size Chart
│
├── Yarn Requirements
│   └── References Yarn Master
│
├── Fabric Requirements
│   └── References Fabric Master
│
├── Production Workflow
│   │
│   ├── Cutting
│   │   ├── Tolerance %
│   │   ├── Input Unit
│   │   ├── Output Unit
│   │   ├── Conversion
│   │   └── Rate
│   │
│   ├── Fusing
│   │   ├── Tolerance %
│   │   └── Rate
│   │
│   ├── Marking
│   │
│   ├── Stitching
│   │   ├── Sub-processes
│   │   ├── Tolerance %
│   │   └── Rate
│   │
│   ├── Trimming & Checking
│   │
│   ├── Ironing
│   │
│   └── Packing
│       ├── Output Unit
│       └── Conversion
│
├── Trim Planning
│   └── References Trim Master
│
├── Packing Material Planning
│   └── References Packing Material Master
│
└── Planned Rates
```

------------------------------------------------------------------------

# 22. LOT Architecture

The intended relationship is:

``` text
                         STYLE MASTER
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
     Materials            Workflow              Rates
        │                     │                     │
 Yarn/Fabric/Trims     Processes/Subprocesses    Planned Rates
 Packing Materials     Tolerance/Units
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                         CREATE LOT
                              │
                              ▼
                       LOT SNAPSHOT
                              │
                              ▼
                    ACTUAL PRODUCTION
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  Actual Materials      Actual Processes       Actual Rates
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    PLANNED vs ACTUAL
```

------------------------------------------------------------------------

# 23. Example End-to-End Style

Example:

``` text
STYLE
SK-203-50

YARN
- 30s VL
- 40s RL

FABRIC
- 30sVL-S/J-Pink-30
- 40sRL-S/J-White-16

TRIMS
- Button-12mm-White
- Elastic-35mm-Lycra

PACKING MATERIAL
- InnerCard-7.5"x11
- BOPP-8.5"x11"+2
- Gaset-5*9.25*2.75flap+1.75
- Carton-24"18"14"

WORKFLOW
Cutting
↓
Fusing
↓
Marking
↓
Stitching
↓
Trimming & Checking
↓
Ironing
↓
Packing

PROCESS CONFIGURATION
Each process can have:
- Tolerance %
- Input unit
- Output unit
- Conversion
- Min rate
- Max rate
- Planned rate
- Sub-processes where applicable
```

------------------------------------------------------------------------

# 24. Style Creation UI --- Functional Expectation

The Style Creation UI should make it possible to configure the complete
Style in a structured way.

A possible organization is:

``` text
Style Creation

1. Basic Information
2. Sizes / Size Chart
3. Colours / Variants / SKU
4. Yarn
5. Fabric
6. Production Workflow
7. Process Configuration
8. Trim Planning
9. Packing Material Planning
10. Rates
11. Review / Save / Version
```

The UI does **not** have to follow this exact screen arrangement. The
important requirement is that all of the underlying business
capabilities remain available.

------------------------------------------------------------------------

# 25. Do Not Hard-Code the Workflow

Different garment styles may have different processes.

Therefore avoid building:

``` text
Every Style = Cutting → Fusing → Stitching → Ironing → Packing
```

as a fixed workflow.

Instead:

``` text
Style
  ↓
Configurable Process List
  ↓
Configurable Sequence
  ↓
Configurable Sub-processes
```

The Style Creator must be able to add/remove/reorder applicable
processes.

------------------------------------------------------------------------

# 26. Default vs Style-Specific Configuration

Where appropriate, the system should support:

``` text
DEFAULT MASTER CONFIGURATION
             ↓
       Style Creation
             ↓
   Use Default OR Override
```

This applies particularly to:

-   Units
-   Unit conversions
-   Process settings
-   Rates
-   Tolerances
-   Other reusable configuration

However, once a Style has its own explicit configuration, the
Style-specific value should take precedence where the business rule says
so.

------------------------------------------------------------------------

# 27. Important Design Principles

### Principle 1 --- Style is the production blueprint

The Style Master must be comprehensive enough to define how a garment is
produced.

### Principle 2 --- LOT is execution

A LOT should inherit the Style configuration rather than rebuilding it
manually.

### Principle 3 --- Use master references

Yarn, Fabric, Trim, Packing Material, Size, Colour, Process, Unit, etc.
should be reusable masters wherever appropriate.

### Principle 4 --- Process configuration must be flexible

Processes, sub-processes, order, tolerance, units, conversion, and rates
must not be unnecessarily hard-coded.

### Principle 5 --- Preserve historical LOT data

A later Style Master edit must not silently change historical/running
LOT configuration.

### Principle 6 --- Support planned vs actual

Style-level planned values should provide the baseline for actual
production comparison.

### Principle 7 --- Units are process-aware

Do not assume Pieces is the only unit throughout the production
lifecycle.

### Principle 8 --- Final output is configurable

Finished output can be Pieces, Dozen, Sets, or Boxes depending on the
Style.

------------------------------------------------------------------------

# 28. Future Implementation Guardrail

**IMPORTANT FOR CLAUDE / FUTURE DEVELOPMENT**

When modifying or extending the ERP:

1.  Treat this document as the baseline business specification for Style
    Creation.
2.  Do not remove any of the above concepts merely to simplify the UI.
3.  Do not convert master references into uncontrolled free-text fields.
4.  Do not hard-code one universal production workflow for all Styles.
5.  Do not hard-code one universal tolerance for all processes.
6.  Do not hard-code Pieces as the only unit.
7.  Do not assume the final packing output is always Pieces.
8.  Do not make Style Master edits retroactively change existing LOTs.
9.  Do not remove process-level rate information because rates may later
    be used for planned-vs-actual comparison.
10. Do not remove Trim/Packing Material planning from Style Creation.
11. Do not remove unit-conversion capability.
12. Do not make the Style Master merely a basic product-name screen; it
    is the **production blueprint**.
13. Any proposed architectural change that affects these principles must
    be explicitly surfaced for business approval before implementation.

------------------------------------------------------------------------

# 29. One-Line Definition

> **Style Master = the complete, versioned production blueprint of a
> garment --- defining its variants, materials, workflow, processes,
> tolerances, units, conversions, trims, packing materials and planned
> rates --- which is used to create LOTs and establish the baseline for
> actual production and planned-vs-actual analysis.**
> ------------------------------------------------------------------------

# 30. LOCKED LOT PRODUCTION WORKFLOW

The following rules are now part of the **locked business
specification**.

A Style Master defines the planned production workflow. When a LOT is
created from that Style, the LOT receives a snapshot of the Style
configuration and executes the workflow process-by-process.

The LOT must track the movement of quantity through every configured
process/stage.

The basic execution model is:

``` text
STYLE MASTER
    |
    | Create LOT
    v
LOT SNAPSHOT
    |
    v
CUTTING
    |
    | Out / Produced
    v
PIECES
    |
    v
PROCESS / STAGE 1
    |
    | Out → In
    v
PROCESS / STAGE 2
    |
    | Out → In
    v
...
    |
    v
IRONING / PACKING
    |
    v
FINAL OUTPUT
    |
    +--> Pieces
    +--> Dozen
    +--> Sets
    +--> Boxes
```

**Important:** the actual quantity received from one process can be less
than the quantity sent into that process. This difference must be
recorded as process loss/rejection/yield variance rather than silently
overwriting quantities.

------------------------------------------------------------------------

# 31. PROCESS GROUPS, STAGES AND SUB-PROCESSES

The system should distinguish between:

1.  **Process Group** - a logical grouping such as `Making`.
2.  **Process / Stage** - an actual production step such as `Fusing`,
    `Stitching`, or `Button`.
3.  **Sub-process** - a more detailed option within a stage where
    required.

For example:

``` text
Making
├── Fusing
├── Stitching
│   ├── Power Table
│   ├── Snitex
│   ├── Helpers
│   └── Contract %
└── Button
```

Another Style may have:

``` text
Making
├── Overlock
├── Flatlock
├── Singer
├── Helper
└── Shift
```

These are examples only. The Style Creator must be able to configure
which processes/stages and sub-processes apply to each Style.

A process/stage should retain its configured:

-   Sequence
-   Input unit
-   Output unit
-   Tolerance %
-   Conversion rule
-   Minimum rate
-   Maximum rate
-   Planned rate
-   Sub-processes
-   Applicable trim/material usage
-   Other process-specific settings

------------------------------------------------------------------------

# 32. LOT PROCESS MOVEMENT: OUT → IN

Every executable LOT process/stage should support an explicit quantity
movement.

Conceptually:

``` text
Previous Process Output
        |
        v
      OUT
        |
        | Delivery / Transfer
        v
Current Process
        |
        v
       IN
```

The system must preserve both values.

### Example

If Cutting produces 100 pieces:

``` text
Cutting Output = 100 pcs
```

Fusing may receive/send:

``` text
Fusing
Out = 100 pcs
In  = 90 pcs
```

The 10-piece difference must remain visible as process loss/yield
difference.

The next process then receives the actual output from Fusing:

``` text
Stitching
Out = 90 pcs
In  = 88 pcs
```

Therefore the chain is:

``` text
Cutting      → 100 pcs
Fusing       → 90 pcs
Stitching    → 88 pcs
Button       → 88 pcs
Final        → 88 pcs
```

The system must **never automatically force the IN quantity to equal the
OUT quantity** merely to make the numbers look consistent.

------------------------------------------------------------------------

# 33. DELIVERY CHALLAN / PROCESS TRANSFER

When goods move from one process/location/vendor to another, the system
should support a Delivery Challan / transfer document.

The provided example shows:

``` text
DELIVERY CHALLAN

Challan No: DC/26-27/015
Date: 2026-09-06

From (Consigner)
MG AKASH

Description:
CD 105 | Fusing
Lot 15

Quantity:
100 pcs
```

The challan should be linked to:

-   LOT
-   Style
-   Process/stage
-   Sending quantity
-   Sending date
-   From party/location
-   To party/location
-   Challan number
-   Document date
-   Document status
-   Relevant signatures/details where applicable

The process card should be able to show the linked challan/document.

Example:

``` text
Fusing

Out
6 Sep · 100 pcs · DC/26-27/015

In
6 Sep · 90 pcs

Bill value
₹1,800 · ₹20.00/pc

Document
View

No trims used at this stage
```

The same model applies to later process transfers.

------------------------------------------------------------------------

# 34. LOT PROCESS CARD

The LOT UI should provide a process/stage card that summarizes execution
and expands to show details.

The card should be capable of displaying:

``` text
Process Name
Actual IN quantity
Actual OUT quantity
Date
Bill value
Effective rate
Linked document / challan
Trim/material usage
Process status
```

Example:

``` text
Fusing                         90 in
                               ₹1,800

Out    6 Sep · 100 pcs · DC/26-27/015
In     6 Sep · 90 pcs

Bill value   ₹1,800 · ₹20.00/pc
Document     View
Trims        No trims used at this stage
```

For Stitching:

``` text
Stitching                      88 in
                               ₹1,500

Out    6 Sep · 90 pcs · DC/26-27/016
In     6 Sep · 88 pcs

Bill value   ₹1,500 · ₹17.05/pc
```

For Button:

``` text
Button                         88 in
                               ₹2,000

Out    6 Sep · 88 pcs · DC/26-27/017
In     6 Sep · 88 pcs

Bill value   ₹2,000 · ₹22.73/pc
```

The UI can be redesigned, but these business values must remain
available.

------------------------------------------------------------------------

# 35. PROCESS RATE / BILL VALUE IN LOTS

The Style Master stores the **planned/default rate** for a process.

When a LOT is created, the planned rate is copied into the LOT snapshot
and should be available for costing and comparison.

During actual production, the LOT records the actual process bill/value.

For a quantity-based process:

``` text
Effective Actual Rate
=
Actual Process Bill Value / Actual Process IN Quantity
```

Example:

``` text
Fusing:
Bill Value = ₹1,800
IN = 90 pcs

Actual Rate = ₹1,800 / 90
            = ₹20.00 per piece
```

``` text
Stitching:
Bill Value = ₹1,500
IN = 88 pcs

Actual Rate = ₹1,500 / 88
            = ₹17.05 per piece
```

``` text
Button:
Bill Value = ₹2,000
IN = 88 pcs

Actual Rate = ₹2,000 / 88
            = ₹22.73 per piece
```

The system should retain both:

-   Planned Style/LOT rate
-   Actual LOT rate

so that the system can compare them later.

Where a process uses another unit, the rate basis must use that
process's configured unit.

------------------------------------------------------------------------

# 36. MAKING COST

Where `Making` is used as a process group, its actual cost should be
derived from the actual costs of its included process/stage entries.

Example:

``` text
Fusing       ₹1,800
Stitching    ₹1,500
Button       ₹2,000
--------------------
Making       ₹5,300
```

Therefore:

``` text
Making Cost = Sum of actual bill values of applicable Making stages
```

Do not treat `Making` as an unrelated manually typed number if its child
process costs already exist.

If the business later requires a separate group-level charge, it may be
added explicitly, but it must not silently duplicate child-stage costs.

------------------------------------------------------------------------

# 37. LOT COST SUMMARY

The LOT should provide a cost summary showing the major components of
actual production cost.

The provided example shows:

``` text
COST SUMMARY

₹139.41 per piece

COST BREAKDOWN

Fabric                    ₹5,600
Wastage tolerance 3%       ₹168
Cutting                     ₹200
Making                    ₹5,300
Trims & accessories          ₹0
Additional costs          ₹1,000
--------------------------------
Total cost               ₹12,268
```

The arithmetic is:

``` text
Fabric                  = ₹5,600
Wastage tolerance       = ₹168
Cutting                 = ₹200
Making                  = ₹5,300
Trims & accessories     = ₹0
Additional costs        = ₹1,000

Total Cost
= 5,600 + 168 + 200 + 5,300 + 0 + 1,000
= ₹12,268
```

The final quantity in the example is:

``` text
First quality = 88 pcs
Rejected      = 12 pcs
Total         = 100 pcs
```

The displayed cost per piece is based on **first-quality output**:

``` text
Cost per First-Quality Piece
=
Total Cost / First Quality Pieces

= ₹12,268 / 88
= ₹139.41 per piece
```

Therefore:

> **The displayed ₹/piece cost must use saleable/first-quality output,
> not rejected quantity, unless the business explicitly chooses another
> costing basis.**

The system should show the costing basis clearly.

------------------------------------------------------------------------

# 38. WASTAGE / TOLERANCE COST

Tolerance/wastage can affect costing.

The example explicitly shows:

``` text
Fabric = ₹5,600
Wastage tolerance = 3%
Wastage amount = ₹168
```

Calculation:

``` text
₹5,600 × 3% = ₹168
```

Therefore the style/LOT should be able to retain:

-   Base material cost
-   Applicable wastage/tolerance %
-   Calculated wastage amount
-   Cost after wastage

The tolerance used for a cost calculation must be traceable to the
applicable Style/LOT configuration.

Do not silently replace the configured tolerance with a hard-coded
percentage.

------------------------------------------------------------------------

# 39. ACTUAL LOT COST COMPONENTS

The LOT cost summary should support at least:

``` text
Fabric
Fabric Wastage / Tolerance
Cutting
Making
Trims & Accessories
Additional Costs
Other configured cost components
Total Cost
```

The system should be able to calculate:

``` text
Total Cost
=
Fabric Cost
+ Wastage/Tolerance Cost
+ Cutting Cost
+ Making Cost
+ Trims & Accessories Cost
+ Additional Costs
+ Other explicitly configured components
```

Zero-value components should remain valid and may be displayed as `₹0`
when the UI uses the component.

------------------------------------------------------------------------

# 40. QUALITY OUTPUT AND COSTING BASIS

The LOT must separately track at least:

-   Total produced/output quantity
-   First-quality quantity
-   Rejected quantity
-   Other quality categories if later configured

Example:

``` text
Total = 100 pcs
First Quality = 88 pcs
Rejected = 12 pcs
```

These quantities must not be confused with process IN/OUT quantities.

For costing:

``` text
First Quality Quantity
```

is the denominator for the displayed **cost per piece** in the reference
workflow.

For production/yield reporting, however, the system should preserve all
quantities so that:

``` text
Production Yield
Reject %
Process Loss
First Quality %
```

can be calculated independently.

------------------------------------------------------------------------

# 41. PLANNED VS ACTUAL: FINAL BUSINESS PURPOSE

The Style Master is not only a workflow template. It is the baseline for
production planning and cost comparison.

At Style level:

``` text
STYLE MASTER

Process
Planned Quantity Rule
Tolerance
Unit
Conversion
Planned Rate
Material Requirement
```

At LOT level:

``` text
LOT

Actual OUT
Actual IN
Actual Output
Actual Bill Value
Actual Rate
Actual Material Consumption
Actual Reject/Loss
Actual Cost
```

Comparison:

``` text
                 PLANNED        ACTUAL       VARIANCE
Process Qty
Process Rate
Process Cost
Material Usage
Material Cost
Final Output
Rejection
Total Cost
Cost / First Quality Piece
```

This comparison is one of the primary reasons the Style Master must be
complete and structured.

------------------------------------------------------------------------

# 42. STYLE → LOT RATE AUTO-APPLICATION

When a LOT is created from a Style:

``` text
Style Master Planned Rate
            ↓
       LOT Snapshot
            ↓
   Actual Production Entry
            ↓
 Planned vs Actual Rate
```

The Style's configured planned/default process rates should be
automatically available in the LOT.

The user should not need to manually re-enter the planned rate for every
LOT.

Actual rate/bill value remains a LOT-level execution value.

This allows the system to show:

``` text
Planned Rate
Actual Rate
Difference
Variance %
```

for every applicable process.

------------------------------------------------------------------------

# 43. STYLE MASTER SNAPSHOT AND IMMUTABILITY OF LOT HISTORY

When a LOT is created, the following Style information must be copied
into a LOT snapshot/version:

-   Style identity
-   Variant/SKU
-   Sizes
-   Colours
-   Yarn requirements
-   Fabric requirements
-   Trim requirements
-   Packing materials
-   Workflow
-   Process order
-   Sub-processes
-   Tolerances
-   Units
-   Conversion rules
-   Planned rates
-   Other relevant production configuration

If the Style Master is edited later:

``` text
OLD LOT
   |
   +--> continues using its original snapshot

NEW LOT
   |
   +--> uses the updated Style Master
```

This is mandatory for historical costing and production reporting.

------------------------------------------------------------------------

# 44. REFERENCE LOT EXAMPLE --- CD 105 / LOT 15

The screenshots provide the following reference execution:

``` text
Style / Product: CD 105
LOT: 15
Date: 6 Sep 2026
```

### Cutting

``` text
Input material: 10.00 kg
Output: 100 pieces
Consumption: 100.00 g/pc
Cutting cost: ₹200
```

The system should retain the relationship between the material quantity
and the resulting pieces.

### Fusing

``` text
Out: 100 pcs
In: 90 pcs
Bill Value: ₹1,800
Effective Rate: ₹20.00/pc
Challan: DC/26-27/015
```

### Stitching

``` text
Out: 90 pcs
In: 88 pcs
Bill Value: ₹1,500
Effective Rate: ₹17.05/pc
Challan: DC/26-27/016
```

### Button

``` text
Out: 88 pcs
In: 88 pcs
Bill Value: ₹2,000
Effective Rate: ₹22.73/pc
Challan: DC/26-27/017
```

### Making Total

``` text
₹1,800 + ₹1,500 + ₹2,000
= ₹5,300
```

### Final Quality

``` text
First Quality = 88 pcs
Rejected      = 12 pcs
Total         = 100 pcs
```

### Cost Summary

``` text
Fabric                         ₹5,600
Fabric wastage/tolerance 3%      ₹168
Cutting                          ₹200
Making                         ₹5,300
Trims & accessories                ₹0
Additional costs               ₹1,000
--------------------------------------
Total                          ₹12,268

Cost per first-quality piece
= ₹12,268 / 88
= ₹139.41
```

This example is a **reference business calculation** and should be used
to validate implementation.

------------------------------------------------------------------------

# 45. STYLE CREATION REQUIREMENTS RECONFIRMED

The Style Creator must therefore allow the business user to configure:

``` text
STYLE
│
├── Style Name / Code
├── Product
├── Sizes
├── Size Chart
├── Colours
├── SKU / Variants
│
├── Yarns
│   └── Yarn Master references
│
├── Fabrics
│   └── Fabric Master references
│
├── Workflow
│   ├── Process Group
│   ├── Process / Stage
│   ├── Sequence
│   ├── Sub-processes
│   ├── Tolerance %
│   ├── Input Unit
│   ├── Output Unit
│   ├── Conversion
│   └── Planned Rate
│
├── Trims
│   ├── Trim Master
│   ├── Quantity
│   ├── Unit
│   ├── Category
│   └── Excess %
│
├── Packing Materials
│   ├── Packing Material Master
│   ├── Quantity
│   ├── Unit
│   ├── Conversion
│   └── Usage Stage
│
└── Planned Cost / Rate Configuration
```

------------------------------------------------------------------------

# 46. NON-NEGOTIABLE IMPLEMENTATION RULES --- ADDITIONAL

The following are now explicitly locked:

1.  A LOT must inherit the Style Master workflow instead of rebuilding
    it manually.
2.  A LOT must preserve a snapshot of the Style configuration used to
    create it.
3.  Every executable process/stage must support actual `OUT` and `IN`
    quantities where applicable.
4.  Process loss between OUT and IN must remain visible.
5.  Process transfers should support linked Delivery Challans/documents.
6.  Actual process bill values must be retained.
7.  Effective actual rate must be calculable from bill value and the
    applicable quantity/unit.
8.  Planned Style rates must be available automatically in the LOT for
    planned-vs-actual comparison.
9.  Making cost should aggregate its actual child-stage costs when
    Making is configured as a process group.
10. The LOT cost summary must support Fabric, Wastage/Tolerance,
    Cutting, Making, Trims & Accessories, Additional Costs, and other
    explicitly configured components.
11. The displayed cost per piece in the reference workflow is calculated
    using **First Quality quantity** as the denominator.
12. First Quality and Rejected quantities must be tracked separately.
13. Process quantities and final quality quantities are different
    concepts and must not be conflated.
14. Cutting output is pieces in the reference workflow, but units remain
    configurable by Style/process where the business requires it.
15. Final Ironing/Packing output may be Pieces, Dozen, Sets, or Boxes.
16. Conversion units may be preset from defaults or
    configured/overridden during Style Creation.
17. Tolerance % is configurable per process; it must not be treated as
    one universal global percentage.
18. Do not hard-code the example values from LOT 15 as universal values.
    They are a reference example of the calculation and UI behavior.
19. UI can change, but the underlying data, calculations, relationships,
    and auditability described in this document must remain.

------------------------------------------------------------------------

# 47. FINAL CLAUDE GUARDRAIL

**CLAUDE MUST TREAT THIS DOCUMENT AS A BUSINESS LOGIC CONTRACT.**

When implementing or modifying the Garments ERP:

-   Do not simplify away Style Master functionality.
-   Do not replace structured master references with uncontrolled text.
-   Do not remove process-level tolerance.
-   Do not remove process-level units/conversions.
-   Do not remove planned rates.
-   Do not remove LOT snapshots.
-   Do not remove OUT/IN process movement.
-   Do not remove Delivery Challan linkage.
-   Do not remove actual process bill values.
-   Do not remove first-quality/rejected tracking.
-   Do not change the cost-per-piece denominator from first-quality
    quantity in the reference costing workflow without explicit business
    approval.
-   Do not make a later Style Master edit alter an existing LOT.
-   Do not hard-code the number or names of production stages.
-   Do not hard-code the final output unit.
-   Do not silently change formulas because a different implementation
    is easier.

If an implementation decision conflicts with this document, **surface
the conflict before changing the business behavior**.

The visual UI may evolve. The business model and calculations may not be
changed silently.

------------------------------------------------------------------------

# 48. COMPACT SYSTEM MODEL

``` text
                    STYLE MASTER
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
   MASTER DATA        WORKFLOW           PLANNED RATES
       │                 │                  │
Yarn/Fabric/Trims   Groups/Stages/       Process rates
Packing/Size/Colour Sub-processes        Min/Max/etc.
       │            Tolerance/Units
       │            Conversion
       └─────────────────┼──────────────────┘
                         │
                    CREATE LOT
                         │
                         ▼
                  LOT SNAPSHOT
                         │
                         ▼
                      CUTTING
                         │
                    Pieces Output
                         │
                         ▼
                 PROCESS/STAGE 1
                    OUT → IN
                         │
                         ▼
                 PROCESS/STAGE 2
                    OUT → IN
                         │
                         ▼
                        ...
                         │
                         ▼
                  IRONING/PACKING
                         │
               Final Unit Conversion
                         │
                         ▼
               FIRST QUALITY / REJECT
                         │
                         ▼
                    COST SUMMARY
                         │
                         ▼
               PLANNED vs ACTUAL
```

> **Locked definition:** Style Master is the versioned production
> blueprint; LOT is the execution snapshot. The Style defines what
> should happen, while the LOT records what actually happened, including
> quantities, process losses, transfers, documents, actual bills,
> quality output, costs, and planned-vs-actual variances.

---

# 47. KAMNA CHANGESET — LOCKED BUSINESS REQUIREMENTS

> **STATUS: CRITICAL / LOCKED**
>
> The following requirements are additional business rules confirmed after review of the Style Master and LOT production workflow. These rules must be preserved in future implementation. Claude must not remove, weaken, reinterpret, or replace them with a simpler generic workflow without explicit business approval.

## 47.1 Inventory / Product SKU is the Source of Truth

- Inventory transactions must **always use/fetch the Product SKU**.
- Do not create uncontrolled free-text product/material identities inside production transactions when a master SKU exists.
- Style, LOT, fabric, trims, packing materials and production transactions should resolve to the appropriate master Product/SKU wherever applicable.
- When a user selects a material/product, the UI should provide a master-data/SKU selector rather than requiring manual re-entry.

## 47.2 LOT Size / Batch Structure

A LOT may represent a production quantity such as:

```text
1 LOT = 500 kg

Example:
500 kg total
├── 100 kg — Colour A
├── 100 kg — Colour B
├── 100 kg — Colour C
├── 100 kg — Colour D
└── 100 kg — Colour E
```

Important:

- A single production requirement may therefore be split into multiple LOTs/batches based on colour or other production dimensions.
- LOT quantities must support both **weight-based** and **piece-based** production.
- Gain/loss must be traceable at LOT level in the relevant unit, including kg where applicable.

## 47.3 Fabric Comes Before Garment Production

The production data model must distinguish the **Fabric stage** from the **Garment stage**.

Conceptually:

```text
Yarn
  ↓
Fabric
  ↓
Fabric Processing / Printing / Dyeing where applicable
  ↓
Cutting
  ↓
Garment Processes
  ↓
Trimming / Checking
  ↓
Ironing
  ↓
Packing
  ↓
Final Output
```

The Style Master must therefore support fabric planning and fabric-related costs before garment-process costing.

## 47.4 Fabric Excess Delivery

The system must support **excess fabric delivery against LOTs**.

Example:

```text
Required fabric → 500 kg
Actual delivery → 515 kg
Excess delivery → 15 kg
```

The excess must remain visible and auditable rather than silently changing the planned requirement.

The system should distinguish at minimum:

- Planned quantity
- Delivered quantity
- Excess quantity
- Consumed quantity
- Balance quantity
- Gain/loss where applicable

## 47.5 Printing / Dyeing Can Change Fabric Weight

Printing, dyeing and similar fabric-processing operations may change the weight of the material.

Therefore:

- Input weight and output weight must be separately recorded where applicable.
- The system must support gain/loss in kg through fabric processing.
- A weight increase after dyeing/printing must not automatically be treated as an error.
- The process should retain the reason/context for the weight change when the business process requires it.

Example:

```text
Fabric before processing = 100 kg
Printing/Dyeing
Fabric after processing  = 103 kg
Gain                     = +3 kg
```

## 47.6 Process Quantity Validation — OUT Cannot Exceed IN

For every executable production process/stage:

> **OUT quantity must be less than or equal to the IN quantity for the same process transaction, unless the process is explicitly configured as a transformation that permits a measured gain.**

For normal garment-making processes:

```text
IN  = 100 pcs
OUT = 98 pcs   ✓

IN  = 100 pcs
OUT = 100 pcs  ✓

IN  = 100 pcs
OUT = 105 pcs  ✗
```

The application must validate this rule before saving/submitting the transaction.

If a business process genuinely produces a gain (for example, a weight-changing fabric process), it must use an explicitly configured gain-capable process/unit rule rather than bypassing the validation.

## 47.7 Cutting → Making → Trimming/Fusing → Receipt

The garment workflow must support the business flow represented by:

```text
Fabric
  ↓
Cutting
  ↓
Making
  ↓
Trimming / Fusing / Other configured stages
  ↓
Received / In
```

The exact sequence remains Style-configurable. Do not hard-code one universal sequence.

Where a stage is performed by another party, the movement must be represented as an outward delivery and subsequent receipt.

## 47.8 Both Insourcing and Outsourcing

Every applicable production process should support:

- **In-house / insourced execution**
- **Outsourced / job-work execution**

The Style Master may define the expected/default mode, while the LOT records the actual execution.

For outsourced work, the LOT process transaction should support:

```text
LOT
 ↓
OUT / Delivery Challan
 ↓
Supplier / Job Worker
 ↓
Process completed
 ↓
IN / Receipt
```

The system must retain the quantity, date, party, document and bill/value associated with the movement.

## 47.9 Master Data Must Be Separate

The following should be maintained as separate reusable master data wherever applicable:

- Product / SKU
- Supplier
- Customer
- Yarn
- Fabric
- Trims
- Packing Materials
- Process / Process Type
- Units
- Other relevant business masters

Transactions must **fetch from these masters and allow the user to choose the appropriate master record**.

Do not duplicate supplier/customer/product definitions as uncontrolled transaction-level text.

## 47.10 Supplier and Customer Selection

When creating a Style, LOT, purchase/receipt, job-work transaction, delivery challan, invoice/bill or related transaction:

- Supplier/customer should be selected from master data.
- Existing master details should be pre-populated where applicable.
- The system should retain the master reference behind the displayed name.

## 47.11 Reminders for Missing Receipts / Material

If material/product/process output is sent out but does not return within the configured expected period, the system must support an alert/reminder.

Example:

```text
OUT → Supplier / Job Worker
Expected return → 3 days
Actual return → Not received

→ Alert / Reminder
```

The expected number of days should be configurable rather than hard-coded.

## 47.12 Bill / Invoice Receipt Tracking

The system must distinguish between:

- Process/material received
- Bill received
- Invoice received, where applicable
- Bill/invoice pending

A process may be completed and material may be received even when its bill has not yet been received.

Therefore:

```text
Material Received = YES
Bill Received     = NO

Status → BILL NOT RECEIVED
```

If no bill/invoice is received within the configured number of days, the system must generate an alert/reminder.

## 47.13 No Price / Missing Rate Handling

When a required price/rate is missing:

- Do not silently insert an arbitrary business value.
- The system should clearly show the missing price/rate.
- If a default value is configured, the system may use that default and clearly identify it as a **default**.
- If a required value is missing and no valid default exists, the system should show an actionable validation/error state.

Example states:

```text
Rate available        → use rate
Default rate available → use default + mark as default
No rate/default       → show Missing Rate / validation warning
```

## 47.14 Additional Costs

Style/LOT costing must support **Additional Costs** outside the standard Fabric, Cutting, Making and Trims categories.

Examples may include business-specific overheads, special charges or other production costs.

Additional costs should support:

- Description
- Amount/rate
- Unit/basis where required
- Planned vs actual where applicable
- Reference/document where applicable

## 47.15 First Quality and Rejected Quantity

Final production must separately track:

- **First Quality** quantity
- **Rejected** quantity
- Total produced/received quantity

The rejected quantity must not be silently discarded from the production record.

Example:

```text
Total final quantity = 100 pcs
First Quality         = 88 pcs
Rejected              = 12 pcs
```

## 47.16 Wastage Tolerance

The general/default wastage tolerance is:

```text
3%
```

However, process/style-specific tolerance configuration remains supported.

The system should distinguish:

- Default/general tolerance
- Style-specific override
- Process-specific tolerance
- Actual wastage
- Tolerance variance

Do not hard-code 3% as the only possible tolerance.

## 47.17 Final Cost Is Based on First-Quality Pieces

The business rule is:

> **The final production cost per piece is calculated against First Quality pieces, not total produced/rejected pieces.**

Reference calculation:

```text
Total Cost = ₹12,268
First Quality = 88 pcs

Cost per First Quality Piece
= ₹12,268 / 88
= ₹139.41 per pc
```

This rule must be preserved in costing and price analysis.

## 47.18 Target Price

The system must support a **Target Price** for a Style and/or applicable production costing scenario.

This is separate from actual cost.

The system should allow comparison such as:

```text
Target Price
Planned Cost
Actual Cost
Variance
Variance %
```

Target price should be stored explicitly and must not be confused with the actual production cost.

## 47.19 GSM — Replace Feeder

Where the existing terminology/UI contains **Feeder** for the relevant fabric measurement/configuration, change it to:

> **GSM**

GSM should be treated as the appropriate fabric characteristic in the Style/Fabric configuration where applicable.

Do not continue displaying the old "Feeder" label for this business concept.

## 47.20 Dyeing Rate and Related Processing Rates

Fabric processing such as dyeing must support its own rate/cost configuration.

The Style/Fabric costing structure should be able to capture applicable rates for:

- Dyeing
- Printing
- Other fabric processing
- Other configured fabric-stage processes

These costs should flow into the relevant planned/actual costing calculations.

## 47.21 Fabric First, Then Garment

The costing and production architecture must preserve the distinction:

```text
FABRIC COST / PROCESSING
        ↓
GARMENT PRODUCTION COST
        ↓
FINAL COST
```

Do not collapse all fabric and garment activities into a single generic process bucket when the business requires separate tracking.

## 47.22 Style Cloning

Style Creation must provide an option to:

> **Clone an existing Style → Edit → Save as a New Style**

The cloned Style should copy the reusable configuration, including where applicable:

- Basic information
- Sizes
- Size chart
- Colours
- SKU/variants
- Yarn
- Fabric
- Workflow
- Processes/stages
- Sub-processes
- Tolerances
- Units/conversions
- Rates
- Trims
- Packing materials
- Target price
- Other style configuration

The new Style must be independently editable after cloning.

## 47.23 Previously Declared Values Must Be Pre-Populated

When editing an existing Style, previously declared values must be **pre-populated**.

The user should not have to re-enter information already saved in the Style Master.

This applies to:

- Units
- Prices/rates
- Tolerances
- Process selections
- Sub-processes
- Material selections
- Quantities
- Conversions
- Other previously declared configuration

When cloning a Style, these values should also be copied as the starting configuration.

## 47.24 Multi-Part Garments / Component Styles

A garment may contain multiple parts/components.

Example:

```text
T-Shirt
├── Part 1
├── Part 2
└── Part 3
```

Different parts may require different Style names/codes or component-level production definitions.

The data model should therefore support component/part relationships without forcing every garment into a single undifferentiated component.

## 47.25 Gain / Loss in LOTs and KG

The LOT system must support gain/loss tracking at both:

- LOT level
- Weight level (kg)

Where applicable, record:

```text
Opening / Input
+ Receipts
- Issues / Consumption
= Expected Balance

Actual Balance

Gain / Loss = Actual - Expected
```

The exact accounting formula may vary by transaction type, but the gain/loss must remain visible and auditable.

## 47.26 Automatic Delivery Challan Generation

For applicable material/process transfers, the system should automatically generate a **Delivery Challan (DC)** from the production transaction.

Example:

```text
LOT Process
   ↓
Send OUT
   ↓
Automatic DC generation
   ↓
Supplier / Job Worker
```

The generated DC must remain linked to:

- LOT
- Style/SKU where applicable
- Process/stage
- Sending party
- Receiving party
- Quantity
- Date
- Relevant material/product

The existing DC numbering/document logic should be reused rather than creating unrelated duplicate document flows.

## 47.27 Trims

Trim planning must support at minimum business examples such as:

- Buttons
- Plastic items
- Elastic
- Labels
- Sewing thread
- Stickers
- Other configurable trims/accessories

Trims must be linked to the relevant master item/SKU where applicable and support quantity, unit, category and excess/tolerance configuration.

## 47.28 Agent Commission and Other Commercial Costs

The costing/commercial model should support **Agent Commission** and other similar commercial charges where applicable.

These should be represented as identifiable cost components rather than hidden inside an unrelated rate.

Where applicable support:

- Commission type/basis
- Rate or amount
- Planned value
- Actual value
- Reference party/agent
- Cost inclusion/exclusion in final costing

## 47.29 Rates Must Remain Available for Planned vs Actual Comparison

All applicable Style Master rates should flow automatically into new LOTs as planned values.

The LOT should then record actual values independently.

```text
STYLE MASTER
   ↓
Planned Rate / Target Price
   ↓
LOT SNAPSHOT
   ↓
Actual Process / Actual Bill
   ↓
Planned vs Actual
```

The system should be able to compare:

- Planned rate vs actual rate
- Planned cost vs actual cost
- Target price vs actual cost
- Process-wise variance
- Style-wise variance
- LOT-wise variance

---

# 48. LOCKED END-TO-END BUSINESS MODEL

The combined Style → LOT model should be understood as follows:

```text
MASTER DATA
│
├── Product / SKU
├── Supplier
├── Customer
├── Yarn
├── Fabric
├── Trims
├── Packing Materials
├── Processes
└── Units
        │
        ▼
STYLE MASTER
│
├── Style Name / Code
├── Product / SKU
├── Sizes / Size Chart
├── Colours / Variants
├── Components / Parts
├── Yarn
├── Fabric
│   ├── GSM
│   ├── Colour
│   ├── Dia
│   └── Processing (Dyeing / Printing etc.)
├── Workflow
│   ├── Process Group
│   ├── Stage
│   ├── Sub-process
│   ├── Sequence
│   ├── Tolerance %
│   ├── Input Unit
│   ├── Output Unit
│   ├── Conversion
│   └── Planned Rate
├── Trims
├── Packing Materials
├── Additional Costs
├── Agent Commission where applicable
├── Target Price
└── Other production rules
        │
        │ Create LOT
        ▼
LOT SNAPSHOT
│
├── Style/SKU snapshot
├── Planned material requirements
├── Planned workflow
├── Planned rates
├── Target price
└── Configuration snapshot
        │
        ▼
FABRIC / MATERIAL RECEIPT
│
├── Planned qty
├── Actual delivered qty
├── Excess delivery
└── Gain/Loss
        │
        ▼
FABRIC PROCESSING
│
├── Dyeing
├── Printing
├── Processing Rate
├── Input kg
├── Output kg
└── Gain/Loss kg
        │
        ▼
CUTTING
│
├── Input kg
├── Output pieces
├── Conversion
├── Cutting rate/cost
└── Gain/Loss where applicable
        │
        ▼
MAKING / CONFIGURED GARMENT WORKFLOW
│
├── Process/Stage 1
├── Process/Stage 2
├── ...
└── Final configured stage
        │
        ├── OUT quantity
        ├── Delivery Challan if transferred
        ├── Supplier / Job Worker if outsourced
        ├── Bill / invoice tracking
        └── IN / Received quantity
        │
        ▼
TRIMMING / CHECKING
        │
        ▼
IRONING
        │
        ▼
PACKING
        │
        ▼
FINAL OUTPUT
│
├── Pieces
├── Dozen
├── Sets
└── Boxes
        │
        ▼
FINAL QUALITY
│
├── First Quality
└── Rejected
        │
        ▼
COSTING
│
├── Fabric
├── Fabric wastage/tolerance
├── Fabric processing
├── Cutting
├── Making
├── Trims & accessories
├── Packing materials
├── Additional costs
├── Agent commission where applicable
└── Other configured costs
        │
        ▼
FINAL COST
│
└── Cost per First-Quality Piece
        │
        ▼
PLANNED vs ACTUAL vs TARGET
```

---

# 49. NON-NEGOTIABLE GUARDRAILS FOR CLAUDE

When modifying this ERP, Claude must treat the following as **business invariants**:

1. **Always use/fetch Product SKU/master data** where a master exists.
2. **LOTs inherit Style Master configuration** and preserve a snapshot.
3. **Do not rebuild the entire workflow manually for every LOT.**
4. **OUT cannot exceed IN** for normal production processes.
5. Explicit gain-capable fabric processes may change weight, but this must be configured and traceable.
6. Support **both insourcing and outsourcing**.
7. Outsourced transfers must support **OUT → Delivery Challan → Supplier/Job Worker → IN/Receipt**.
8. Supplier and Customer must come from separate master data.
9. Support configurable reminders when expected material/process output is not received.
10. Track **material received separately from bill/invoice received**.
11. Missing rates must show a warning/error unless a configured default exists; never invent a value.
12. Preserve **Additional Costs**.
13. Preserve **First Quality and Rejected** quantities.
14. Default/general wastage tolerance is **3%**, but process/style overrides remain possible.
15. **Final cost per piece is based on First Quality pieces.**
16. Support **Target Price** independently from actual cost.
17. Use **GSM**, not Feeder, for the relevant fabric characteristic.
18. Support **Dyeing, Printing and other fabric-processing rates**.
19. Keep **Fabric and Garment** production/costing conceptually distinct.
20. Provide **Clone Style** functionality.
21. Previously saved Style values must be **pre-populated** when editing.
22. Support multi-part/component garments.
23. Track **gain/loss in LOTs and kg** where applicable.
24. Support **automatic Delivery Challan generation** for applicable transfers.
25. Trims must support buttons, plastic and other configured trim types.
26. Support **Agent Commission** and similar commercial costs.
27. Preserve planned rates for **Planned vs Actual** comparison.
28. Do not hard-code one universal workflow for all Styles.
29. Do not hard-code Pieces as the only unit.
30. Do not make Style Master changes retroactively modify an existing LOT.
31. Do not remove process-level tolerance, conversion, rate, or unit configuration.
32. Do not collapse master data into uncontrolled free-text transaction fields.
33. Do not silently overwrite quantity differences; preserve gain/loss/rejection/variance.
34. Do not hide pending bills/invoices when production material has already been received.
35. Do not remove any existing business requirement from this specification merely to simplify the UI.
36. If a proposed implementation change conflicts with any locked rule above, **surface the conflict for explicit business approval before changing the rule**.

---

# 50. REFERENCE EXAMPLES FOR VALIDATION

## Example A — Normal Garment Process

```text
IN  = 100 pcs
OUT = 90 pcs

Valid.
Process loss = 10 pcs.
```

## Example B — Invalid Normal Process

```text
IN  = 100 pcs
OUT = 105 pcs

Invalid.
The system must block or require an explicitly configured gain-capable process.
```

## Example C — Fabric Weight Gain

```text
Before dyeing = 100 kg
After dyeing  = 103 kg
Gain          = 3 kg
```

Valid only when the fabric-processing process is configured to allow measured gain.

## Example D — Final Cost

```text
Fabric                         ₹5,600
Fabric wastage/tolerance 3%      ₹168
Cutting                          ₹200
Making                         ₹5,300
Trims & accessories                ₹0
Additional costs               ₹1,000
--------------------------------------
Total                          ₹12,268

First Quality = 88 pcs
Rejected      = 12 pcs

Final Cost / First Quality Piece
= ₹12,268 / 88
= ₹139.41/pc
```

## Example E — Outsourced Process

```text
LOT
 ↓
100 pcs OUT
 ↓
Automatic DC
 ↓
Supplier / Job Worker
 ↓
90 pcs IN
 ↓
10 pcs process loss/variance
 ↓
Bill pending
```

The LOT should show the DC, supplier, OUT quantity, IN quantity, bill status and variance.

---

# 51. FINAL DEFINITION

> **The Garments ERP Style Master is the versioned production blueprint from which LOTs are created. It defines the Product/SKU, materials, fabric and fabric processing, garment components, configurable production workflow, process tolerances, units/conversions, trims, packing materials, rates, additional costs, target price and other production rules. LOTs execute a frozen Style snapshot while recording actual material movement, OUT/IN quantities, gain/loss, quality, delivery challans, supplier/customer/job-work movements, bills/invoices and actual costs. Final costing is based on First Quality output, with planned-vs-actual and target-price comparison available throughout.**

**This specification is a locked business baseline for future Claude implementation. Any change to these business invariants requires explicit business-owner approval.**
