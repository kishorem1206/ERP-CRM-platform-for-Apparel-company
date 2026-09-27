# CRM / ERP UI DESIGN SYSTEM — MASTER SOURCE OF TRUTH

> **Purpose:** This document is the single source of truth for generating, redesigning, or modifying every page of the CRM/ERP application.
>
> **Primary visual reference:** The provided CRM screenshots.
>
> **Critical rule:** **DO NOT redesign, recolor, resize, restructure, or otherwise alter the left navigation. The current left navigation is already approved and must remain exactly as it is.**
>
> All improvements described below apply primarily to the **inside/content area of every page**.

---

# 1. CORE DESIGN DIRECTION

The entire CRM/ERP must visually feel like one polished enterprise application.

The design language is based on exactly **three primary visual families**:

1. **BLUE**
2. **PURPLE**
3. **WHITE**

The UI may use lighter and darker shades of these three families, plus neutral greys required for readability, borders, separators, disabled states, and backgrounds.

The overall appearance should be:

* Premium
* Enterprise-grade
* Clean
* Modern
* Information-dense without feeling cluttered
* Highly structured
* Professional
* Consistent across CRM, ERP, reports, dashboards, forms, tables, workflows and detail pages

Do **not** introduce unrelated dominant colours.

---

# 2. COLOUR SYSTEM

## 2.1 Primary Blue

Use blue as the main application/action colour.

### Primary Blue

```text
Blue 900: #064FAF
Blue 800: #0755B8
Blue 700: #1764C0
Blue 600: #2563C7
Blue 500: #3B73D1
```

Recommended primary:

```text
#0755B8
```

Use for:

* Primary buttons
* Active navigation states
* Primary links
* Selected controls
* Important interactive elements
* Progress indicators
* Active tabs
* Focus states
* Primary chart elements
* Workflow progression

---

# 3. PURPLE SYSTEM

Purple is the secondary/accent colour.

### Purple

```text
Purple 900: #4338A8
Purple 800: #4F46B5
Purple 700: #5B52C7
Purple 600: #6D63DC
Purple 500: #7C70E8
Purple 400: #9389F0
Purple 300: #B8B0F7
Purple 200: #D9D5FC
Purple 100: #ECEAFF
Purple 50:  #F6F5FF
```

Recommended primary purple:

```text
#5B52C7
```

Use purple for:

* Secondary actions
* Selected/active secondary states
* Workflow stages
* Tags
* Secondary metrics
* Analytics highlights
* Report categories
* AI-related features
* Important but non-primary information
* Special status indicators
* Section accents

Purple should complement blue rather than compete with it.

---

# 4. WHITE SYSTEM

White is the dominant content-surface colour.

```text
White:       #FFFFFF
Off White:   #FAFBFC
Surface:     #F7F8FA
Soft Surface:#F3F5F8
```

Use:

```text
#FFFFFF
```

for:

* Cards
* Tables
* Forms
* Modals
* Dropdowns
* Detail panels
* Main content surfaces

Use:

```text
#F7F8FA
```

for:

* Main page backgrounds
* Dashboard backgrounds
* Empty spaces
* Content canvas

---

# 5. SUPPORTING NEUTRALS

Neutral colours are allowed only to support the Blue / Purple / White visual system.

```text
Text 900: #111827
Text 800: #172033
Text 700: #334155
Text 600: #64748B
Text 500: #94A3B8
Text 400: #A8B1BF

Border:       #E2E6EC
Border Light: #EDF0F4

Background:   #F7F8FA
```

Avoid excessive dark grey.

The interface should remain visually light.

---

# 6. STATUS COLOURS

Status colours may be used when semantically necessary.

They must be visually restrained and should appear primarily as small badges, indicators or icons rather than large page backgrounds.

## Success

```text
Green:       #2DB88A
Green Light: #E7F8F2
```

## Warning

```text
Amber:       #F2A93B
Amber Light: #FFF5E5
```

## Error

```text
Red:       #D85C68
Red Light: #FDECEE
```

## Information

Use Blue.

```text
#0755B8
```

## Special / Secondary

Use Purple.

```text
#5B52C7
```

---

# 7. LEFT NAVIGATION — LOCKED / DO NOT CHANGE

## IMPORTANT

The existing left navigation shown in the approved screenshot is **FINAL**.

Do not:

* Change its colour
* Change its width
* Change its hierarchy
* Change its icons
* Change its spacing
* Change its typography
* Change its active states
* Convert it to white
* Make it grey
* Make it collapsible unless already supported
* Replace its visual treatment
* Add unnecessary gradients
* Change the bottom user section
* Change the Saved Filters section
* Change the Create button styling

### The current navigation must remain visually equivalent to the approved screenshot.

It should continue using the strong blue treatment with:

* White navigation text
* White/light icons
* Blue active/hover states
* Existing spacing
* Existing hierarchy
* Existing section labels
* Existing user profile area

### DO NOT REBUILD THE SIDEBAR.

Treat it as an already-approved component.

---

# 8. GLOBAL CONTENT AREA

Everything **inside** the navigation should use the same visual language.

The content area should generally follow:

```text
Page Background
    ↓
Page Header
    ↓
Toolbar / Filters
    ↓
Cards / Tables / Forms / Reports
```

Recommended page background:

```text
#F7F8FA
```

Content surfaces:

```text
#FFFFFF
```

---

# 9. PAGE HEADER

Every major page should have a consistent header.

Example:

```text
CRM / LEADS

Leads
Manage prospects, pipeline activity and customer opportunities.
```

Hierarchy:

### Breadcrumb

Small uppercase text.

```text
CRM / LEADS
```

Style:

```text
font-size: 12px
font-weight: 600
letter-spacing: 0.08em
color: #8A93A3
```

### Page Title

```text
Leads
```

Style:

```text
font-size: 28px–32px
font-weight: 700
color: #111827
```

### Description

```text
Manage prospects, pipeline activity and customer opportunities.
```

Style:

```text
font-size: 14px–16px
color: #8A93A3
```

---

# 10. TOP SEARCH BAR

The global search should visually resemble the approved design.

White rounded search container.

```text
background: #FFFFFF
border: 1px solid #E2E6EC
border-radius: 10px
```

Search icon:

```text
#8A93A3
```

Placeholder:

```text
#9AA3B2
```

Keyboard shortcut:

```text
⌘K
```

or

```text
Ctrl K
```

depending on platform.

---

# 11. BUTTON SYSTEM

## Primary Button

Blue.

```text
background: #0755B8
color: #FFFFFF
border-radius: 8px
```

Example:

```text
+ Create Lead
```

Hover:

```text
#064FAF
```

---

## Secondary Button

White with blue border/text.

```text
background: #FFFFFF
border: 1px solid #C9D6EA
color: #0755B8
border-radius: 8px
```

---

## Purple Button

Use when the action is secondary/special.

```text
background: #5B52C7
color: #FFFFFF
```

---

## Ghost Button

```text
background: transparent
color: #0755B8
```

Use sparingly.

---

# 12. CARDS

Cards should resemble the clean white cards from the reference UI.

```text
background: #FFFFFF
border: 1px solid #E6EAF0
border-radius: 12px
```

Optional subtle shadow:

```text
0 2px 8px rgba(20, 40, 80, 0.05)
```

Cards should NOT have:

* Heavy shadows
* Thick borders
* Random gradients
* Excessive rounded corners
* Large decorative illustrations

---

# 13. CARD HEADER

Example:

```text
PIPELINE FUNNEL

Open leads by stage
```

Small label:

```text
font-size: 12px
font-weight: 600
letter-spacing: 0.08em
color: #8A93A3
```

Heading:

```text
font-size: 16px–18px
font-weight: 600
color: #172033
```

---

# 14. KPI / METRIC CARDS

Dashboard metric cards should follow the reference style.

Example:

```text
TOTAL PIPELINE

₹300.3Cr

7 open leads
```

Structure:

```text
[Label]                         [Icon]

Large Number

Supporting information
```

Large number:

```text
font-size: 26px–32px
font-weight: 700
color: #111827
```

Supporting text:

```text
font-size: 13px
color: #9299A5
```

Icon containers should use very light blue/purple backgrounds.

Example:

```text
Blue icon:
background: #EEF5FF
border: #C9DCF8
color: #0755B8
```

Purple icon:

```text
background: #F0EEFF
border: #DDD9FC
color: #5B52C7
```

---

# 15. TABLE DESIGN

Tables are extremely important throughout the CRM/ERP.

They should be clean and dense without appearing cramped.

## Table Header

```text
background: #F7F8FA
color: #687386
font-size: 11px–12px
font-weight: 600
text-transform: uppercase
```

Use subtle bottom border:

```text
#E5E9EF
```

---

## Table Rows

```text
background: #FFFFFF
```

Border:

```text
#EDF0F4
```

Hover:

```text
#F5F8FD
```

Selected:

```text
#EEF5FF
```

---

# 16. TABLE PRIMARY TEXT

Use dark text:

```text
#172033
```

Secondary information:

```text
#7C8797
```

Links:

```text
#0755B8
```

Never use underlines unless necessary.

---

# 17. STATUS BADGES

Badges should be compact and rectangular with slightly rounded corners.

### Active

```text
background: #E8F3FF
color: #1670C5
```

### Approved

```text
background: #E8F7EF
color: #4D9638
```

### Waiting

```text
background: #FFF3D8
color: #C78316
```

### Completed

```text
background: #E8F7F1
color: #218C70
```

### Cancelled

```text
background: #FDEBED
color: #C14F5C
```

### Purple status

```text
background: #EEEAFE
color: #5B52C7
```

Badges should generally use:

```text
font-size: 11px
font-weight: 700
padding: 3px 8px
border-radius: 4px
```

---

# 18. TABS

Tabs should follow the blue/purple visual language.

Example:

```text
Overview   Activity   Notes   Documents
```

Inactive:

```text
color: #8A93A3
```

Active:

```text
color: #0755B8
font-weight: 600
```

Active underline:

```text
background: #0755B8
height: 2px
```

Purple can be used for special secondary tab groups.

---

# 19. FORMS

Forms must feel premium and clean.

Input:

```text
background: #FFFFFF
border: 1px solid #DDE3EB
border-radius: 8px
```

Height:

```text
40px–44px
```

Focus:

```text
border-color: #0755B8
box-shadow: 0 0 0 3px rgba(7,85,184,0.10)
```

Labels:

```text
font-size: 13px
font-weight: 600
color: #334155
```

Placeholder:

```text
#9AA3B2
```

---

# 20. DROPDOWNS

Dropdowns should look like white floating cards.

```text
background: #FFFFFF
border: 1px solid #E1E6ED
border-radius: 8px
box-shadow: 0 8px 24px rgba(20,40,80,0.10)
```

Selected option:

```text
background: #EEF5FF
color: #0755B8
```

Hover:

```text
background: #F5F8FD
```

---

# 21. FILTERS

Filters should be visually compact.

Example:

```text
[ All Leads ▼ ] [ Owner ▼ ] [ Status ▼ ] [ Date ▼ ]
```

Use white backgrounds with subtle borders.

Active filter:

```text
background: #EEF5FF
border-color: #BFD5F4
color: #0755B8
```

Purple may be used for advanced/special filters.

---

# 22. SEARCH + FILTER TOOLBAR

Recommended structure:

```text
[ Search........................ ]

[ Filter ] [ Status ] [ Owner ] [ Date ]

                         [ Export ] [ + Create ]
```

The toolbar must not become visually heavy.

Keep controls aligned and evenly spaced.

---

# 23. DASHBOARDS

Dashboard pages should use the reference screenshot as the primary visual inspiration.

A dashboard should consist of:

```text
Page Header

Alerts / Notifications

KPI Cards

Primary Analytics

Secondary Analytics

Recent Activity / Tables
```

Avoid overly colourful dashboards.

Use:

* Blue for primary metrics
* Purple for secondary analytics
* Green only for positive/success
* Amber only for warnings
* Red only for errors
* White cards
* Light grey background

---

# 24. ALERT BANNERS

Alerts should be subtle.

### Error / Overdue

```text
background: #FFF5F6
border: 1px solid #F1CDD2
color: #D85C68
```

### Warning

```text
background: #FFF9ED
border: 1px solid #F2DFC0
color: #D99020
```

### Information

```text
background: #F0F6FF
border: 1px solid #CADCF5
color: #0755B8
```

### Success

```text
background: #EDF9F4
border: 1px solid #CBEADD
color: #218C70
```

---

# 25. PROGRESS BARS

Use blue/purple gradients only when useful.

Recommended:

```text
Blue → Purple
```

Example gradient:

```text
linear-gradient(90deg, #0755B8 0%, #7469E8 100%)
```

Track:

```text
#F0F2F6
```

Success:

```text
#2DB88A
```

Do not use rainbow progress bars.

---

# 26. CHARTS

Charts must follow the same colour hierarchy.

## Primary series

```text
#0755B8
```

## Secondary series

```text
#5B52C7
```

## Positive

```text
#2DB88A
```

## Warning

```text
#F2A93B
```

## Negative

```text
#D85C68
```

Gridlines:

```text
#EDF0F4
```

Chart background:

```text
transparent / white
```

Avoid unnecessarily saturated chart colours.

---

# 27. DONUT / PIE CHARTS

Use a restrained palette.

Example:

```text
Open: #0755B8
Won:  #2DB88A
Lost: #D85C68
Secondary: #5B52C7
```

The centre should remain white.

---

# 28. KANBAN / BOARD VIEW

Kanban should visually follow the screenshot.

Columns:

```text
background: #F1F3F6
border-radius: 10px
```

Column headers:

```text
font-size: 13px
font-weight: 700
color: #697386
text-transform: uppercase
```

Cards:

```text
background: #FFFFFF
border: 1px solid #E2E6EC
border-radius: 8px
```

Card title:

```text
color: #172033
font-weight: 600
```

Metadata:

```text
color: #8A93A3
```

Labels:

Use Blue / Purple / status colours.

---

# 29. TASK CARDS

Task cards should visually resemble the reference screenshot.

Structure:

```text
Task title

Assigned person / department

[Reference ID / Tag]

        Comments    Activity    Due Date
```

Use:

```text
border-radius: 8px
background: #FFFFFF
```

Reference tags can use:

```text
Blue:   #1595D1
Purple: #6958C8
Orange: #F0A02A
```

Orange is allowed here only as a semantic legacy/reference tag colour and must not become a primary application colour.

---

# 30. DETAIL PAGES

Detail pages should follow:

```text
Breadcrumb
Page Title
Primary Actions

Summary Card

Tabs

Main Information
Related Information
Activity
Documents
History
```

Example:

```text
CRM / LEADS / LEAD-1025

Acme Textiles Pvt Ltd

[Edit] [Convert] [More]

--------------------------------

Lead Information

Company
Acme Textiles Pvt Ltd

Owner
Alex

Status
Qualified
```

---

# 31. DETAIL PAGE SIDE PANELS

Side panels should use white cards.

Avoid dark panels unless they are specifically part of the locked navigation.

Use:

```text
background: #FFFFFF
border-left: 1px solid #E2E6EC
```

---

# 32. ACTIVITY TIMELINE

Activity feeds should follow the screenshot's clean timeline style.

Timeline line:

```text
#D9DFE8
```

Timeline icon:

Blue or Purple.

Activity title:

```text
#334155
```

Timestamp:

```text
#9AA3B2
```

Important links:

```text
#0755B8
```

---

# 33. MODALS

Modal:

```text
background: #FFFFFF
border-radius: 12px
box-shadow: 0 20px 60px rgba(20,40,80,0.18)
```

Header:

```text
font-size: 20px
font-weight: 700
color: #111827
```

Footer:

```text
border-top: 1px solid #EDF0F4
```

Primary CTA:

Blue.

Secondary CTA:

White / bordered.

---

# 34. DRAWERS

Drawers should feel like an extension of the page.

```text
background: #FFFFFF
box-shadow: -8px 0 30px rgba(20,40,80,0.10)
```

Header:

```text
border-bottom: 1px solid #E7EAF0
```

---

# 35. ICONOGRAPHY

Use one consistent icon family throughout the application.

Icons should generally be:

```text
16px–20px
stroke-based
```

Primary icon colour:

```text
#0755B8
```

Secondary:

```text
#5B52C7
```

Muted:

```text
#8792A3
```

Avoid mixing radically different icon styles.

---

# 36. TYPOGRAPHY

Use a clean modern sans-serif.

Preferred:

```text
Inter
```

Fallback:

```text
-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

## Typography hierarchy

### Page title

```text
28–32px
700
```

### Section title

```text
18–20px
600–700
```

### Card title

```text
15–17px
600
```

### Body

```text
14px
400
```

### Small metadata

```text
12–13px
400–500
```

### Labels

```text
11–12px
600
```

---

# 37. BORDER RADIUS

Use a controlled radius system.

```text
4px  — badges
6px  — small controls
8px  — inputs/buttons/cards
10px — larger cards
12px — major containers
```

Do not make everything excessively rounded.

---

# 38. SHADOW SYSTEM

Shadows should be extremely subtle.

### Small

```text
0 1px 3px rgba(20,40,80,0.05)
```

### Card

```text
0 2px 8px rgba(20,40,80,0.05)
```

### Dropdown

```text
0 8px 24px rgba(20,40,80,0.10)
```

### Modal

```text
0 20px 60px rgba(20,40,80,0.18)
```

Never use heavy black shadows.

---

# 39. SPACING SYSTEM

Use an 8px-based spacing system.

```text
4px
8px
12px
16px
20px
24px
32px
40px
48px
64px
```

Default content padding:

```text
32px
```

Card padding:

```text
20px–24px
```

---

# 40. PAGE GRID

Use a responsive grid.

Example:

```text
12-column grid
```

Dashboard:

```text
KPI cards:
4 columns each

Large analytics:
8 columns

Secondary analytics:
4 columns
```

Maintain consistent gutters:

```text
16px–24px
```

---

# 41. RESPONSIVENESS

The UI must work across:

* Desktop
* Laptop
* Tablet
* Smaller screens

Do not destroy information hierarchy on smaller screens.

Tables may horizontally scroll where necessary rather than becoming unreadable.

---

# 42. CRM MODULES

The following CRM pages must use this design system:

* Dashboard
* Leads
* Contacts
* Companies
* Deals
* Pipeline
* Activities
* Calls
* Meetings
* Tasks
* Emails
* WhatsApp
* Notes
* Documents
* Quotes
* Sales
* Reports
* Analytics
* Settings
* User Management
* Permissions
* AI Assistant
* Security
* Admin

---

# 43. ERP MODULES

The same visual system must be applied to:

* Sales
* Purchasing
* Inventory
* Production
* Manufacturing
* Warehouse
* Products
* Product SKUs
* Suppliers
* Customers
* Orders
* Work Orders
* Purchase Orders
* Stock Movements
* Materials
* Processes
* Quality
* Finance
* Accounting
* Reports
* Audit
* Administration

---

# 44. WORKFLOW UI

Workflow-heavy ERP pages should use Blue → Purple progression.

Example:

```text
Lead
  ↓
Qualified
  ↓
Proposal
  ↓
Negotiation
  ↓
Won
```

Active stage:

```text
Blue
```

Completed stages:

```text
Purple / Blue
```

Current stage:

```text
Blue with stronger emphasis
```

Future stages:

```text
Light grey / light blue
```

---

# 45. WORKFLOW CARDS

Workflow cards should contain:

```text
Step number

Step name

Owner

Status

Date

Actions
```

Use a vertical or horizontal progression depending on available space.

Do not make workflow diagrams visually noisy.

---

# 46. REPORT DESIGN

Reports should be especially polished.

Every report should follow:

```text
Report Header
↓
Filters
↓
Summary Metrics
↓
Charts
↓
Detailed Table
↓
Export / Print
```

Use white cards against a very light background.

Blue and purple should establish visual hierarchy.

---

# 47. REPORT EXPORT / PDF STYLE

When generating downloadable reports, the visual identity must remain consistent with the web application.

Use:

```text
Blue
Purple
White
Light neutral backgrounds
```

Avoid introducing unrelated colours into PDFs.

Report headings should use the primary blue/purple identity.

Tables should use white rows and subtle borders.

---

# 48. EMPTY STATES

Empty states should be minimal.

Example:

```text
No leads found

There are no leads matching the selected filters.

[ Clear Filters ]
```

Use:

* Light blue/purple icon
* Dark heading
* Muted description
* Blue CTA

Avoid giant illustrations.

---

# 49. LOADING STATES

Use skeleton loaders rather than generic spinners where possible.

Skeleton:

```text
#E9EDF3
```

Animated shimmer should be subtle.

---

# 50. TOASTS / NOTIFICATIONS

Success:

```text
white surface
green accent/icon
```

Information:

```text
white surface
blue accent/icon
```

Warning:

```text
white surface
amber accent/icon
```

Error:

```text
white surface
red accent/icon
```

Use a coloured icon/accent rather than filling the entire notification with colour.

---

# 51. HOVER STATES

Hover states must be subtle.

White components:

```text
background → #F7F9FC
```

Blue buttons:

```text
#0755B8 → #064FAF
```

Table rows:

```text
#FFFFFF → #F5F8FD
```

---

# 52. FOCUS STATES

Accessibility-friendly focus:

```text
outline: 2px solid #5B52C7
outline-offset: 2px
```

or a subtle blue focus ring.

Never remove keyboard focus visibility.

---

# 53. ACTIVE STATES

The active state hierarchy is:

```text
Primary active:
Blue

Secondary active:
Purple

Selected content:
Very light Blue

Special selected:
Very light Purple
```

Example:

```text
Blue active background:
#EEF5FF

Purple active background:
#F0EEFF
```

---

# 54. COLOUR PROPORTION

The approximate visual distribution throughout the application should be:

```text
WHITE / LIGHT SURFACES: 60–70%

BLUE: 15–25%

PURPLE: 5–15%

OTHER SEMANTIC COLOURS: 5% or less
```

Blue and purple are accents and hierarchy tools.

Do not turn every component blue or purple.

---

# 55. WHAT MUST NOT HAPPEN

Do NOT:

* Make internal pages dark
* Use random gradients
* Use rainbow colour palettes
* Use excessive green
* Use excessive orange
* Use excessive red
* Make every card colourful
* Change the approved left navigation
* Turn the left navigation white
* Introduce a second unrelated design language
* Use huge rounded cards
* Use excessive shadows
* Use inconsistent icon sets
* Use multiple unrelated fonts
* Use random component spacing
* Create different UI styles for different modules
* Make CRM and ERP look like separate applications

---

# 56. CRITICAL SIDEBAR RULE

The current left navigation is the **reference implementation**.

It is already approved.

Therefore:

```text
LEFT NAVIGATION = LOCKED
```

All future UI work must adapt to it.

The content area should visually feel like it belongs to the same application.

The sidebar's strong blue establishes the application's brand identity.

The inside pages should therefore use:

```text
Blue
+
Purple
+
White
```

to continue that identity.

---

# 57. VISUAL RELATIONSHIP BETWEEN SIDEBAR AND CONTENT

The visual hierarchy should be:

```text
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  BLUE SIDEBAR      WHITE / LIGHT CONTENT AREA           │
│                                                         │
│  Navigation        Page Header                          │
│                    ─────────────────────                 │
│                    Filters / Actions                     │
│                    ─────────────────────                 │
│                    White Cards                           │
│                    Blue + Purple Analytics               │
│                                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The sidebar is the strongest visual element.

The content area is intentionally lighter.

---

# 58. FINAL IMPLEMENTATION RULE

When creating **any new page**, first ask:

### 1. Does the existing left navigation remain untouched?

If no → fix it.

### 2. Does the page use the same Blue / Purple / White system?

If no → fix it.

### 3. Does the page look like it belongs to the same application?

If no → fix it.

### 4. Are cards, tables, forms, filters and buttons using the same component language?

If no → fix it.

### 5. Are colours being used for hierarchy rather than decoration?

If no → simplify.

---

# 59. MASTER DESIGN TOKENS

Use these as the canonical values.

```css
:root {

  /* =========================
     BRAND
     ========================= */

  --brand-blue-900: #064FAF;
  --brand-blue-800: #0755B8;
  --brand-blue-700: #1764C0;
  --brand-blue-600: #2563C7;
  --brand-blue-500: #3B73D1;

  --brand-purple-900: #4338A8;
  --brand-purple-800: #4F46B5;
  --brand-purple-700: #5B52C7;
  --brand-purple-600: #6D63DC;
  --brand-purple-500: #7C70E8;
  --brand-purple-400: #9389F0;

  /* =========================
     LIGHT SURFACES
     ========================= */

  --white: #FFFFFF;
  --surface-50: #FAFBFC;
  --surface-100: #F7F8FA;
  --surface-200: #F3F5F8;

  /* =========================
     TEXT
     ========================= */

  --text-900: #111827;
  --text-800: #172033;
  --text-700: #334155;
  --text-600: #64748B;
  --text-500: #94A3B8;
  --text-400: #A8B1BF;

  /* =========================
     BORDERS
     ========================= */

  --border: #E2E6EC;
  --border-light: #EDF0F4;

  /* =========================
     STATUS
     ========================= */

  --success: #2DB88A;
  --success-light: #E7F8F2;

  --warning: #F2A93B;
  --warning-light: #FFF5E5;

  --danger: #D85C68;
  --danger-light: #FDECEE;

  /* =========================
     SELECTED STATES
     ========================= */

  --blue-selected: #EEF5FF;
  --purple-selected: #F0EEFF;

  /* =========================
     RADIUS
     ========================= */

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 10px;
  --radius-xl: 12px;

  /* =========================
     SPACING
     ========================= */

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* =========================
     SHADOWS
     ========================= */

  --shadow-sm:
    0 1px 3px rgba(20, 40, 80, 0.05);

  --shadow-card:
    0 2px 8px rgba(20, 40, 80, 0.05);

  --shadow-dropdown:
    0 8px 24px rgba(20, 40, 80, 0.10);

  --shadow-modal:
    0 20px 60px rgba(20, 40, 80, 0.18);

  /* =========================
     TYPOGRAPHY
     ========================= */

  --font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}
```

---

# 60. FINAL DESIGN COMMAND

**Recreate the CRM/ERP UI as a single cohesive enterprise application based on the supplied reference screenshots.**

**The existing left navigation is already perfect and is LOCKED. Do not redesign it.**

For every page inside the navigation:

* Use the same visual language.
* Use **Blue + Purple + White** as the primary colour system.
* Use lighter/darker shades of these colours to create hierarchy.
* Keep backgrounds predominantly white/light grey.
* Use blue for primary actions and primary information.
* Use purple for secondary/special information.
* Use semantic colours only where necessary.
* Use clean white cards.
* Use subtle borders.
* Use subtle shadows.
* Use consistent typography.
* Use consistent spacing.
* Use consistent buttons, tables, filters, forms, badges, tabs, modals and charts.
* Keep the UI information-dense but clean.
* Maintain enterprise CRM/ERP usability.
* Do not introduce unrelated visual styles between modules.

### Most important rule:

> **SIDEBAR = KEEP EXACTLY AS CURRENTLY APPROVED.**
>
> **CONTENT AREA = REWORK EVERYTHING TO FEEL LIKE THE SAME BLUE + PURPLE + WHITE DESIGN SYSTEM.**

The result should look like a **single premium CRM + ERP product**, not a collection of independently designed pages.
