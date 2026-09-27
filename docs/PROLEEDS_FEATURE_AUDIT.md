# Proleeds Feature Audit
> Phase 1 — Screenshot analysis + existing-system comparison  
> Created: 2026-09-03 | Screenshots analysed: 30

---

## Methodology

Every significant capability visible across all 30 Proleeds screenshots was catalogued below.
Each row answers:

- **What does Proleeds do here?**
- **Does our existing system handle it?**
- **Should we act, and how?**

Status values: `EXISTS` · `PARTIAL` · `MISSING` · `BETTER ALREADY` · `NOT RELEVANT`  
Recommendation values: `KEEP` · `IMPROVE` · `ADD` · `IGNORE`

---

## A. DASHBOARD / BUSINESS OVERVIEW

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| A1 | Dashboard | Total Opportunities widget | Donut chart: Cold/Warm/Hot/Won/Lost lead counts + total | CRM dashboard has pipeline KPI tiles but no temperature breakdown | PARTIAL | IMPROVE — add lead temperature field + temperature KPIs to dashboard |
| A2 | Dashboard | Total Contacts widget | Donut chart: Leads vs Customers + conversion % | We track persons/orgs but not a Lead→Customer conversion rate KPI | PARTIAL | IMPROVE — add conversion % calculation to dashboard |
| A3 | Dashboard | Total Follow-Ups widget | Donut: Due Today / Upcoming / Overdue / Completed | CrmActivity has is_done + schedule_from but no dashboard summary widget | PARTIAL | IMPROVE — add follow-up summary widget drawing from CrmActivity |
| A4 | Dashboard | WhatsApp device stats | Active devices, Automation/Single/Bulk message counts | WhatsApp module tracks messages but no per-device/type breakdown on dashboard | PARTIAL | IMPROVE — add WhatsApp stats tile when WhatsApp is configured |
| A5 | Dashboard | WhatsApp Official stats | Quality Rating, Remaining Quota, Sent count, Pricing | WhatsApp Cloud API is integrated; quota data is from Meta API | MISSING | ADD — fetch Meta API quality/quota stats and surface on dashboard |
| A6 | Dashboard | Marketing stats | Ad Spent, CPL (cost per lead), ROAS | No marketing spend tracking | MISSING | ADD (Phase 15) — simple ad spend entry with auto-calculated CPL/ROAS |
| A7 | Dashboard | Revenue stats | Income, Expense, Net Profit, Profitability % | ERP has Invoice/Payment models; finance module exists | PARTIAL | IMPROVE — pull actual revenue from Invoice/Payment into CRM dashboard |
| A8 | Dashboard | Leaderboard | Staff ranked by conversions + revenue generated | No staff performance ranking | MISSING | ADD — lead conversion + quote value per assigned_to user, shown in dashboard |
| A9 | Dashboard | Email Stats | Subscribers, Sent, Delivered, Failed, Open Rate, Unsubscribes | CrmEmail tracks sent/failed status; no open-rate tracking | PARTIAL | IMPROVE — add sent/failed counts from crm_emails to dashboard |
| A10 | Dashboard | Automation Stats | Active workflows, Disabled, Tasks Executed, Time Saved | No workflow engine yet | MISSING | ADD (Phase 5+) — add after workflow engine is built |
| A11 | Dashboard | Calendar Booking stats | Booked/Cancelled/Show Up/No Show/Rescheduled | No calendar/appointment module | MISSING | ADD (Phase 9) — after calendar module is built |
| A12 | Dashboard | LMS stats | Courses, Students, Comments, Completion | Not relevant for apparel ERP | NOT RELEVANT | IGNORE |
| A13 | Dashboard | Webinar stats | Registrations, Show Up, During Pitch, Sales funnel | Not relevant for apparel ERP | NOT RELEVANT | IGNORE |
| A14 | Dashboard | Sales Data block | Sales Reps, Sales Calls, No Show, Show Up, Pitches, Total Sales | Partially relevant — we have salespeople/orders | PARTIAL | IMPROVE — use actual SO data; ignore call/pitch tracking unless added later |

---

## B. SHOP / BUSINESS PROFILE (Lead Generation)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| B1 | Setup Shop | Public business profile | Company name, slug, phone, city, country, address visible publicly | Company model has basic details; no public profile page | MISSING | ADD — extend Company settings with a "Business Profile" section (Phase 2/settings) |
| B2 | Setup Shop | Shop link + QR code | Shareable public URL for the business profile | No public URL or QR code | MISSING | ADD — low priority; useful for lead generation forms later |
| B3 | Setup Shop | Publish toggle | Makes the shop profile publicly visible | No public pages | MISSING | IGNORE for now — we don't need a public-facing landing page yet |
| B4 | Setup Shop | About Shop (rich text) | Business description shown on public profile | Company model has no description field | MISSING | ADD — simple `description` column on Company; show in settings |
| B5 | Setup Shop | Header/Body Script | Custom script injection for analytics/pixels | No script injection | NOT RELEVANT | IGNORE — we're not running a public web property |
| B6 | Setup Shop | Meta Title/Description | SEO metadata for public shop page | N/A | NOT RELEVANT | IGNORE |
| B7 | Social dropdown | Social media management | Post scheduling, account connections (Dashboard/Posts/Create/Connect) | No social integration | NOT RELEVANT | IGNORE — not in scope for apparel ERP |
| B8 | URL's dropdown | URL shortener, Spaces, Domains | Short link management | No URL shortener | NOT RELEVANT | IGNORE |

---

## C. CRM LEAD MANAGEMENT

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| C1 | CRM Kanban | Kanban pipeline board | Drag-and-drop cards across stage columns | EXISTS — leads/page.tsx has full HTML5 drag-and-drop kanban | EXISTS | KEEP |
| C2 | CRM Kanban | Pipeline selector | Dropdown to switch between named pipelines | EXISTS — pipeline filter in leads page | EXISTS | KEEP |
| C3 | CRM Kanban | Lead count + value per column | "4 Leads ₹0.00" shown under each stage header | Our kanban shows lead count; no ₹ column total | PARTIAL | IMPROVE — add sum(lead_value) per stage column to kanban header |
| C4 | CRM Kanban | Lead card info | Name, phone, email, lead value, created/updated, assigned staff avatar | lead_value EXISTS; phone/email require person lookup | PARTIAL | IMPROVE — show person's phone and primary email on lead card |
| C5 | CRM Kanban | Card quick actions | Icons for edit, add task, calendar, WhatsApp message | We have edit; no quick-add task/follow-up/WhatsApp from card | PARTIAL | IMPROVE — add WhatsApp quick action icon on lead card (links to WhatsApp page) |
| C6 | CRM Kanban | Lead type chip | "87 Total · 85 Lead · 2 Customer" filter chips | No such type filtering | MISSING | ADD — leads can be type Lead or Customer via existing type_id |
| C7 | CRM Kanban | Lead temperature | Cold/Warm/Hot classification visible in dashboard | No temperature field | MISSING | ADD — add `temperature` column (cold/warm/hot) to crm_leads |
| C8 | CRM List | List view toggle | Switch between Kanban and List/Table view | EXISTS — list/kanban toggle in leads page | EXISTS | KEEP |
| C9 | CRM List | Bulk select + bulk actions | Checkbox selection + Assign/Move Stage/Archive | EXISTS — bulk action bar implemented (Phase 4) | EXISTS | KEEP |
| C10 | CRM List | CSV Import | Import leads from CSV file | EXISTS — 3-step import wizard (Phase 4) | EXISTS | KEEP |

---

## D. OPPORTUNITY / LEAD DETAIL

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| D1 | Add Opportunity | Tabbed detail modal | Tabs: Opportunity, Additional Info, Call Logs, Follow-up, Notes, Appointments | Lead detail is a full page, not modal. No Call Logs or Appointments tab | PARTIAL | IMPROVE — add Notes tab and Follow-up tab to lead detail page |
| D2 | Add Opportunity | Opportunity Name | Lead title | EXISTS — `title` on CrmLead | EXISTS | KEEP |
| D3 | Add Opportunity | Contact Name, Email, Phone | Contact details linked to lead | EXISTS — via person_id relationship | EXISTS | KEEP |
| D4 | Add Opportunity | City | Contact location | Missing from CrmPerson/CrmLead | MISSING | ADD — add `city` field to CrmPerson |
| D5 | Add Opportunity | Pipeline + Stage dropdowns | Which pipeline and which stage | EXISTS — pipeline_id + stage_id on CrmLead | EXISTS | KEEP |
| D6 | Add Opportunity | Type (Lead/Customer) | Contact type classification | EXISTS — type_id on CrmLead (CrmLeadType) | EXISTS | KEEP |
| D7 | Add Opportunity | Status | Open/Won/Lost etc. | EXISTS — `status` on CrmLead | EXISTS | KEEP |
| D8 | Add Opportunity | Tags | Multi-tag input | EXISTS — CrmLeadTag many-to-many | EXISTS | KEEP |
| D9 | Add Opportunity | Lead Value | Monetary value of the opportunity | EXISTS — `lead_value` Numeric(14,4) on CrmLead | EXISTS | KEEP |
| D10 | Add Opportunity | Staff Assign | Assign a team member to the lead | EXISTS — `assigned_to` on CrmLead | EXISTS | KEEP |
| D11 | Add Opportunity | Call Logs tab | Track call history with the contact | No call log model | MISSING | ADD (Phase 4/activities) — extend CrmActivity type="call" with duration + outcome |
| D12 | Add Opportunity | Appointments tab | Schedule meetings/demos with the contact | No appointment model; CrmActivity partially covers this | PARTIAL | IMPROVE — add appointment_type/calendar link to CrmActivity |

---

## E. CONFIGURABLE PIPELINES

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| E1 | Pipelines list | Multiple named pipelines | 14 pipelines: India MART, White Label, E-Commerce, Retail, etc. | EXISTS — CrmPipeline is fully configurable | EXISTS | KEEP |
| E2 | Pipelines list | Pipeline CRUD | Create / Edit / Delete pipelines | EXISTS — backend API + CRM settings page | EXISTS | KEEP |
| E3 | Pipelines list | Bulk delete selected | Checkbox select + Delete Selected button | EXISTS via settings; could be improved | PARTIAL | IMPROVE — add multi-select delete to settings/pipelines |
| E4 | Add pipeline modal | Pipeline name field | Name the pipeline | EXISTS | EXISTS | KEEP |
| E5 | Add pipeline modal | Stages with color picker | Each stage has a text input + color swatch + drag handle + delete | Stage color EXISTS (color column planned); drag reorder EXISTS in settings | PARTIAL | IMPROVE — add `color` column to CrmPipelineStage; expose color picker in settings |
| E6 | Add pipeline modal | Stage drag-to-reorder | Drag handles to change stage order | EXISTS — sort_order column; UI needs drag | PARTIAL | IMPROVE — add drag-to-reorder in pipeline settings UI |
| E7 | Pipelines list | is_won / is_lost flags | Won and Lost are special terminal stages | EXISTS — is_won, is_lost on CrmPipelineStage | EXISTS | KEEP |

---

## F. CONTACT / PERSON PIPELINE MEMBERSHIP (HIGH VALUE)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| F1 | Contact Info — Pipelines & Stages tab | Contact in multiple pipelines simultaneously | A contact can have active opportunities in India MART Pipeline AND White Label Pipeline at the same time without duplication | MISSING — a person can have multiple leads (each in one pipeline) but there's no unified "pipelines this person is in" view | MISSING | ADD — create `/crm/persons/{id}/pipelines` endpoint that returns all leads grouped by pipeline with stage strip |
| F2 | Contact Info — stage strip | Visual horizontal stage journey | All stages of a pipeline shown as pills in order; current stage highlighted; others greyed | No such visualization exists | MISSING | ADD — add stage history strip component to person detail page |
| F3 | Contact Info — scrollable stages | Horizontal scroll for many stages | India MART Pipeline has 16 stages; visible as scrollable horizontal strip | N/A | MISSING | ADD — part of F2 implementation |
| F4 | Contact Info — current stage pill | Current stage highlighted differently | Active stage shown as filled/colored pill; others are empty outlines | N/A | MISSING | ADD — part of F2 implementation |

---

## G. CONTACT 360

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| G1 | Contact Info | Multi-tab contact view | FOLLOW UPS · NOTES · PIPELINES & STAGES · CONTACT · OPPORTUNITY in one modal | Lead detail page has Activities and Emails tabs; no person-centric 360 view | PARTIAL | IMPROVE — build a Person/Contact 360 page with all tabs |
| G2 | Contact Info | Follow-ups tab on contact | Shows all follow-ups for this specific contact | CrmActivity can filter by person_id | PARTIAL | IMPROVE — add follow-up tab to person detail page |
| G3 | Contact Info | Notes tab | Free-text notes attached to a contact | No standalone Notes model; only activity comments | MISSING | ADD — add `crm_notes` table (person_id / lead_id / organization_id, body, created_by) |
| G4 | Contact Info | Opportunity tab | All opportunities/leads for this contact | Partial — leads list can filter by person | PARTIAL | IMPROVE — add opportunities tab to person detail |

---

## H. STAGE HISTORY (HIGH VALUE)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| H1 | Implicit in pipeline strip | Stage change audit trail | Every time a lead moves to a new stage, the move is recorded with timestamp + who changed it | No stage history table | MISSING | ADD — create `crm_lead_stage_history` table (lead_id, from_stage_id, to_stage_id, changed_by, changed_at, note) |
| H2 | Implicit | Stage journey visualization | Show completed → current → future stages visually | No such component | MISSING | ADD — render stage history on lead detail page (Phase 3 of our plan) |
| H3 | Implicit | Time-in-stage analytics | How long did a lead spend in each stage? | No data captured | MISSING | ADD (Phase 15 analytics) — derive from stage_history timestamps |

---

## I. FOLLOW-UP MANAGEMENT

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| I1 | Follow-up page | Dedicated follow-up list | Separate view distinct from activities | CrmActivity serves this role but the frontend activities page is generic | PARTIAL | IMPROVE — add Due Today / Upcoming / Overdue / Completed filter tabs to activities page |
| I2 | Follow-up | Status tabs: All / Due Today / Upcoming / Overdue / Completed | Filter follow-ups by urgency | No such tabs | MISSING | ADD — backend endpoint `/crm/activities?tab=overdue` etc.; frontend tab UI |
| I3 | Follow-up | Due date tracking | Each follow-up has a due date | EXISTS — `schedule_from` on CrmActivity | EXISTS | KEEP (rename schedule_from → due_date in API response if needed) |
| I4 | Follow-up | Overdue detection | If due_date < now and not done → overdue | EXISTS partially — rotten_at on leads; no general overdue query for activities | PARTIAL | IMPROVE — backend query: is_done=false AND schedule_from < now |
| I5 | Follow-up | Contact linkage | Follow-up shows contact name, email, phone | EXISTS — CrmActivity.person_id | EXISTS | KEEP |
| I6 | Follow-up | Staff assignment | Assign a follow-up to a team member | EXISTS — CrmActivity.assigned_to | EXISTS | KEEP |
| I7 | Follow-up | Bulk delete + refresh | Select multiple and delete | MISSING from activities frontend | MISSING | ADD — bulk delete to activities/follow-up page |
| I8 | Follow-up | Filter by staff + date range | Staff dropdown + date range picker | No staff/date filter on activities page | MISSING | ADD — filter controls to activities page |

---

## J. NOTES

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| J1 | Contact Info NOTES tab | Notes on contacts | Free-text notes with author + timestamp | CrmActivity.comment is only notes-like field; no dedicated notes entity | MISSING | ADD — `crm_notes` table; show in Contact 360 and Lead detail |
| J2 | Notes | Edit/delete notes | Notes can be updated or removed | N/A | MISSING | ADD — with edit permission = author or admin |

---

## K. WORKFLOW AUTOMATION (HIGHEST VALUE)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| K1 | Lead Automation list | Workflow list with folders | Workflows organized in named folders; columns: Name, Allow Re-entry, Total Contacts, Completed, Last Updated, Status, History | No workflow engine | MISSING | ADD (Phase 5) — critical feature |
| K2 | Lead Automation list | Workflow status toggle | Active/Paused per workflow | N/A | MISSING | ADD |
| K3 | Lead Automation list | LOGS button | View execution history per workflow | N/A | MISSING | ADD |
| K4 | Workflow builder | Visual node-based canvas | Pan/zoom canvas with draggable nodes | No workflow builder | MISSING | ADD (Phase 6) — build with React flow or pure canvas |
| K5 | Workflow builder | Trigger node: Stage Changed | "When a contact's stage is changed in selected pipeline, automation will trigger" | Celery task exists (mark_rotten_leads) but no generic trigger system | MISSING | ADD |
| K6 | Workflow builder | Trigger node: Contact Added to Pipeline | "When a contact is added to selected pipeline, automation will trigger" | N/A | MISSING | ADD |
| K7 | Workflow builder | Action: Internal Notification | Send an in-app notification to a staff member | Notification model exists | PARTIAL | IMPROVE — wire notification model into workflow actions |
| K8 | Workflow builder | Action: WhatsApp Message | Send a WhatsApp message to the contact | WhatsApp send API exists | PARTIAL | IMPROVE — expose as workflow action |
| K9 | Workflow builder | Action: Add/Update to CRM | Update a field on the contact/lead | N/A | MISSING | ADD |
| K10 | Workflow builder | Condition node | Branch: IS Hot Lead → YES/NO | N/A | MISSING | ADD |
| K11 | Workflow builder | Delay node | Wait X hours/days before next step | N/A | MISSING | ADD — implement via Celery ETA |
| K12 | Workflow builder | Execute Automation | Trigger another workflow | N/A | MISSING | ADD (Phase 7) |
| K13 | Workflow settings | Allow Re-entry toggle | Contact can enter same workflow again when enabled | N/A | MISSING | ADD — track per-contact per-workflow executions to prevent duplicates |
| K14 | Workflow settings | Schedule Enable/Disable | Activate workflow on a date/time; deactivate on another | N/A | MISSING | ADD |
| K15 | Workflow settings | Specific Time | Run actions only at a certain time of day | N/A | MISSING | ADD |
| K16 | Workflow builder | Test Workflow button | Run workflow manually for a test contact | N/A | MISSING | ADD (Phase 7) |
| K17 | Workflow list | Pre-Built workflows | Templates for common automation patterns | N/A | MISSING | ADD (Phase 7) — seed common apparel workflows |
| K18 | Workflow list | Folder organization | Group workflows in named folders | N/A | MISSING | ADD |

---

## L. TASKS + PROJECTS + WORKSPACES

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| L1 | Operations/Tasks | Workspace concept | Top-level grouping ("Tiruppur Factory") | No workspace model | MISSING | ADD (Phase 8) — Workspace → Project → Section → Task |
| L2 | Tasks board | Board view (Kanban) | Tasks shown as cards in section columns | No task module | MISSING | ADD |
| L3 | Tasks board | List, Report, Calendar, Time Logs views | Multiple ways to view tasks | N/A | MISSING | ADD |
| L4 | Tasks board | My Tasks / Team Members / Favorites | Personal task management + team visibility | N/A | MISSING | ADD |
| L5 | Tasks board | Sections as columns | Within a project, sections become Kanban columns | N/A | MISSING | ADD |
| L6 | Tasks | Time Logs | Track time spent per task | N/A | MISSING | ADD — useful for production/costing context |

---

## M. UNIFIED COMMUNICATION INBOX

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| M1 | Inbox | Unified conversation list | All WhatsApp + Instagram conversations in one panel | WhatsApp has its own 3-panel inbox page; Email has separate inbox page | PARTIAL | IMPROVE — merge WhatsApp inbox into a channel-agnostic inbox with channel badges |
| M2 | Inbox | Channel badges | Green WhatsApp / Red Instagram icons on conversation rows | WhatsApp channel tracked | PARTIAL | IMPROVE — add channel indicator to existing WhatsApp inbox |
| M3 | Inbox | Starred / Unread / WA Groups tabs | Filter conversations by category | No filtering tabs in our WhatsApp inbox | MISSING | ADD — starred + unread filters to WhatsApp inbox |
| M4 | Inbox | 811 total conversations | High-volume conversation handling | WhatsApp inbox exists with pagination | PARTIAL | KEEP — already supports large volumes |
| M5 | Inbox | New Conversation button | Start a new outbound conversation | Our WhatsApp page has a send panel | EXISTS | KEEP |
| M6 | Inbox | Message composer with templates | Type + emoji + attachment + template picker + send | EXISTS — WhatsApp page has template selector | EXISTS | KEEP |

---

## N. CALENDAR

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| N1 | Calendar | Monthly calendar view | Standard month grid | No calendar page | MISSING | ADD (Phase 9) — calendar showing activities with schedule_from dates |
| N2 | Calendar | All Calendars selector | Filter by calendar type | N/A | MISSING | ADD |
| N3 | Calendar | Status colors | Booked (blue), Cancelled (red), Show Up (green), No Show (yellow) | N/A | MISSING | ADD — map to CrmActivity types/statuses |
| N4 | Calendar | Appointments sub-section | Separate tab for appointment bookings | N/A | MISSING | ADD — appointment_type field on CrmActivity |

---

## O. SETTINGS — STAFF

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| O1 | Settings/Staff | Visual staff card grid | Photo, name, role tag, email, phone, active toggle | Admin page manages users but no visual card grid | PARTIAL | IMPROVE — add a CRM-friendly team/staff view page |
| O2 | Settings/Staff | Active/inactive toggle per staff | Disable a staff member from CRM | User `is_active` flag exists | EXISTS | KEEP |

---

## P. SETTINGS — TAGS, VALUES, FIELDS (Custom Fields)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| P1 | Settings sidebar | Tags section | Manage global tag list with colors | EXISTS — CrmTag with name + color | EXISTS | KEEP — expose in CRM settings sidebar |
| P2 | Settings sidebar | Values section | Lookup values (dropdown option lists) | No Values/lookup table | MISSING | ADD — `crm_lookup_values` table for dropdown options (lead types, sources, etc.) as user-configurable |
| P3 | Settings sidebar | Fields section | Custom field definitions per entity | No custom fields | MISSING | ADD (Phase 11) — `crm_custom_field_defs` + `crm_custom_field_values` |

---

## Q. SETTINGS — DOMAIN

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| Q1 | Domain Settings | Company domain registration | Register domain (e.g. tiruppurfactory.com) with DNS verification | No domain management | MISSING | ADD (low priority) — simple domain + DNS verified flag on Company |
| Q2 | Domain Settings | DNS Configuration instructions | Guide user through DNS record setup | N/A | MISSING | ADD with Q1 |

---

## R. SETTINGS — VAULT (File Manager)

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| R1 | Vault | Centralized file/media store | Folders + files; Images/Video/Documents/Audio/Other; Search; Sort | `FileAttachment` model exists in master; no centralized vault UI | PARTIAL | ADD (Phase 12) — build vault using existing FileAttachment or a new vault table |
| R2 | Vault | Storage usage meter | Shows 215.19 MB used | N/A | MISSING | ADD — count file sizes from vault table |
| R3 | Vault | Project folders | Files organized in project folders | N/A | MISSING | ADD — folder entity with parent_id for nesting |
| R4 | Vault | Grid/List view toggle | Switch between card grid and table list | N/A | MISSING | ADD |
| R5 | Vault | File type filters | All Media / Images / Video / Documents / Audio / Other | N/A | MISSING | ADD — filter by MIME type category |

---

## S. SETTINGS — INTEGRATIONS / APP STORE

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| S1 | App Store | Facebook integration | Connect Facebook page with form mapping for leads | No Facebook integration | MISSING | ADD (Phase 13) — webhook for Facebook Lead Ads |
| S2 | App Store | Instagram integration | Connected status + disconnect | No Instagram integration | MISSING | ADD (Phase 13) — Instagram DM webhook |
| S3 | App Store | Pabbly integration | Connect to Pabbly for automation routing | No Pabbly integration | MISSING | IGNORE — use webhooks instead |
| S4 | App Store | Connect LLMs | Configure LLM provider (OpenAI/Anthropic) for AI features | No AI integration | MISSING | ADD (Phase 17) — AI config stored per company, not hardcoded |
| S5 | App Store | Integration status indicators | Connected / Disconnected / Test connection | No integrations page | MISSING | ADD (Phase 13) — unified integrations dashboard |

---

## T. SETTINGS — NOTIFICATIONS + RECOVER

| # | Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|---|-----------|---------|--------------|-----------------|--------|----------------|
| T1 | Settings sidebar | Notifications | Notification preferences per user | Notification model exists; no preferences UI | PARTIAL | IMPROVE — add notification preferences to settings |
| T2 | Settings sidebar | Recover | Data recovery / soft-delete restore | No recover feature | MISSING | ADD (Phase 18) — implement soft-delete on key CRM entities + recover UI |

---

## U. APPAREL-SPECIFIC ANALYSIS

These are capabilities Proleeds shows that need to be adapted (not copied) for our apparel/textile context:

| # | Feature | Proleeds approach | Our better approach | Recommendation |
|---|---------|-------------------|--------------------|----|
| U1 | Pipeline stages | India MART: New Lead→Order→Payment→Dispatch | Our: Enquiry→Sample→Order→Production→QC→Dispatch→Invoice | ADD — seed pipelines via migration, user can edit |
| U2 | WhatsApp automation | Send WhatsApp on stage change | Same — but also trigger production alerts (Dispatch stage → auto WhatsApp to customer) | ADD (Phase 5) |
| U3 | Lead→Order connection | Proleeds: no ERP backend | Our: CrmLead.sales_order_id already links to SalesOrder | BETTER ALREADY — we already have this |
| U4 | Production visibility in CRM | Not in Proleeds | CRM lead detail should show production status from SalesOrder→ProductionLot | ADD (Phase 16) |
| U5 | Wholesale buyer pipeline | Configurable in Proleeds | Configurable in our system too; just seed better default stages | KEEP + seed |
| U6 | White Label pipeline | Proleeds has it | Our pipeline model supports it; just need sample data | KEEP + seed |
| U7 | Export buyer pipeline | Not shown in Proleeds | Our model supports it | ADD as seeded example |

---

## SUMMARY — PRIORITY MATRIX

### Must Add (High Value, Missing)
1. **Lead temperature** (`cold`/`warm`/`hot`) — 1 column on crm_leads, 1 filter
2. **Stage history table** (`crm_lead_stage_history`) — audit every stage change
3. **Contact 360 / multi-pipeline view** — `/crm/persons/{id}/pipelines` + frontend stage strip
4. **Notes model** (`crm_notes`) — free-text notes on persons, leads, organizations
5. **Follow-up tabs** (Due Today / Upcoming / Overdue / Completed) — filter on CrmActivity
6. **Workflow automation engine** — trigger/action/delay/condition model + Celery executor
7. **Visual workflow builder** — node canvas frontend
8. **Tasks / Projects / Workspaces** — Workspace→Project→Section→Task hierarchy
9. **Calendar view** — render CrmActivity due dates on a monthly calendar
10. **File Vault** — centralized file manager

### Should Improve (Partial, Valuable)
- Lead card shows phone + email from linked person
- Lead column totals (sum of lead_value per stage)
- Dashboard: leaderboard widget, revenue from ERP invoices, WhatsApp stats
- Pipeline settings: stage color picker + drag-to-reorder
- Activities page: staff filter, date range, bulk delete
- WhatsApp inbox: starred/unread tabs + channel badges

### Already Exists — Keep As-Is
- Configurable pipelines (CrmPipeline + CrmPipelineStage)
- Lead Kanban with drag-and-drop
- Lead Value field, Status, Tags, Source, Type, Assigned To
- Persons, Organizations, Tags
- Activities (basic follow-up tracking)
- Quotes + Line Items
- Email with SMTP config
- WhatsApp messaging
- CRM Dashboard (basic)
- Bulk actions, CSV import

### Ignore (Not Relevant)
- LMS (courses, students, completion)
- Webinar stats
- Affiliate program
- Community module
- App Store (use webhooks instead of Pabbly)
- URL shortener
- Public shop/social posting features

---

## RECOMMENDED IMPLEMENTATION ORDER

Building on our existing 18-phase plan, these Proleeds-derived additions fit as:

| Our Phase | What to build | Proleeds source |
|-----------|--------------|-----------------|
| Phase 2 (CRM relationships) | Contact 360, Notes, Stage history, Lead temperature, Person 360 page | F, G, H, J, A1 |
| Phase 3 (Pipelines + stage history) | Stage history table, pipeline stage colors, stage strip visual | E5, H1-H3 |
| Phase 4 (Follow-ups + activities) | Due Today/Upcoming/Overdue tabs, staff filter, date range, calendar | I1-I8, N1-N4 |
| Phase 5 (Workflow automation) | Trigger/action/delay/condition model + Celery executor | K1-K18 |
| Phase 6 (Visual workflow builder) | Node canvas, drag-and-drop builder frontend | K4-K16 |
| Phase 7 (Workflow execution) | Execution history, re-entry controls, test mode, LOGS | K13, K16 |
| Phase 8 (Tasks + workspaces) | Workspace→Project→Section→Task | L1-L6 |
| Phase 9 (Calendar) | Monthly calendar from CrmActivity schedule_from | N1-N4 |
| Phase 10 (Unified inbox) | Channel badges, starred/unread in WhatsApp inbox | M1-M6 |
| Phase 11 (Tags + custom fields) | CRM Settings: Tags UI, Values/lookups, custom field defs | P1-P3 |
| Phase 12 (File vault) | Vault with folders, upload, type filters, storage meter | R1-R5 |
| Phase 13 (Integrations) | Integrations page: WhatsApp, Facebook Lead Ads, Instagram | S1-S5 |
| Phase 14 (Notifications) | Notification preferences + workflow-triggered notifications | T1 |
| Phase 15 (Dashboard/reporting) | Leaderboard, lead temperature donut, follow-up donut, revenue tiles | A1-A14 |
| Phase 16 (CRM↔ERP) | Production status on lead detail, ERP traceability | U4 |
| Phase 17 (AI) | LLM config per company, AI assistant on leads/contacts | S4 |
| Phase 18 (Hardening) | Soft-delete, recover, audit trail, security review | T2 |

---

*Last updated: 2026-09-03 — Phase 1 audit complete. Proceed to Phase 2.*
