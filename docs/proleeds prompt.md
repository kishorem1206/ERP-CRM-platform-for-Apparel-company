You are working on my existing CRM + ERP application.

I have supplied a reference set of 30 screenshots from Proleeds.

You MUST inspect the actual screenshots supplied with this task before making implementation decisions.

The screenshots are a COMPETITIVE PRODUCT REFERENCE.

IMPORTANT:

DO NOT CLONE PROLEEDS.

DO NOT rebuild Proleeds.

DO NOT copy Proleeds branding, logo, colors, exact UI, proprietary wording or exact layouts.

Instead:

EXTRACT THE FUNCTIONAL IDEAS, WORKFLOWS, RELATIONSHIPS, AUTOMATION PATTERNS AND PRODUCTIVITY FEATURES THAT WOULD MAKE MY EXISTING CRM BETTER.

============================================================
PRIMARY GOAL
============================================================

Upgrade my existing CRM using the strongest useful ideas visible in the Proleeds screenshots.

The result should be:

MY EXISTING CRM
+
THE BEST MISSING PROLEEDS-STYLE CAPABILITIES
+
MY APPAREL/TEXTILE BUSINESS WORKFLOWS
+
MY EXISTING ERP
+
A BETTER MODERN UX

It should NOT become a Proleeds clone.

============================================================
STEP 1 — INSPECT EVERYTHING FIRST
============================================================

Before modifying code:

1. Inspect every supplied Proleeds screenshot.
2. Catalogue every visible feature.
3. Inspect my existing codebase.
4. Inspect PostgreSQL schema/models.
5. Inspect existing backend APIs.
6. Inspect frontend routes/components.
7. Inspect existing CRM modules.
8. Inspect existing permissions.
9. Inspect existing notifications.
10. Inspect existing workflow/automation capabilities.
11. Inspect existing integrations.
12. Inspect existing tasks/calendar/communications.

Do not assume a feature is missing.

Verify it.

============================================================
STEP 2 — CREATE A PROLEEDS FEATURE INVENTORY
============================================================

Create:

/docs/PROLEEDS_FEATURE_AUDIT.md

For EVERY meaningful capability visible in the screenshots, create:

| Screenshot | Feature | What it does | Existing system | Status | Recommendation |
|------------|---------|--------------|-----------------|--------|----------------|

Status must be one of:

EXISTS
PARTIAL
MISSING
BETTER ALREADY
NOT RELEVANT

Recommendation:

KEEP
IMPROVE
ADD
IGNORE

Do this before implementation.

============================================================
SCREENSHOT AREAS TO ANALYSE
============================================================

The supplied screenshots show several distinct areas.

You must analyse all of them.

------------------------------------------------------------
A. DASHBOARD / BUSINESS OVERVIEW
------------------------------------------------------------

Extract useful concepts from the dashboards:

- Total opportunities
- Total contacts
- Total follow-ups
- Lead generation metrics
- Cold leads
- Warm leads
- Hot leads
- Won leads
- Lost leads
- Customer counts
- Conversion percentage
- Due today
- Upcoming
- Overdue
- Completed
- WhatsApp device statistics
- Marketing statistics
- Revenue
- Expense
- Net profit
- Profitability
- ROAS
- CPL
- Leaderboard
- Team performance
- Email statistics
- Automation statistics
- LMS/calendar statistics where relevant

DO NOT blindly implement all metrics.

Determine which metrics are actually useful for MY CRM/ERP.

Use real backend data.

No fake dashboard numbers.

------------------------------------------------------------
B. SHOP / BUSINESS PROFILE
------------------------------------------------------------

The screenshots show a configurable business/shop setup.

Extract useful concepts such as:

- business name
- slug
- phone
- city
- country
- address
- logo
- profile image
- public shop/profile
- shop link
- QR code
- business description
- header script
- body script
- meta title
- meta description

Determine which belong in my:

Company Settings
Business Profile
Public Profile
Tenant Configuration

Do not duplicate existing company settings.

------------------------------------------------------------
C. CRM LEAD MANAGEMENT
------------------------------------------------------------

The screenshots show a visual pipeline-based lead management system.

Analyse:

- pipeline selector
- stages
- cards
- lead/contact information
- contact status
- opportunity status
- search
- filters
- quick actions
- lead value
- staff assignment
- tags
- stage movement
- creation date
- update date
- contact type

Implement only missing capabilities.

------------------------------------------------------------
D. OPPORTUNITY DETAIL
------------------------------------------------------------

The opportunity modal contains concepts including:

- Opportunity Name
- Contact Name
- Email
- Phone
- City
- Pipeline
- Stage
- Type
- Status
- Created At
- Updated At
- Tags
- Lead Value
- Staff Assignment

Compare this against the existing Opportunity model.

If my current Opportunity model is weaker:

improve it.

Do NOT create a second opportunity system.

------------------------------------------------------------
E. CONFIGURABLE PIPELINES
------------------------------------------------------------

THIS IS ONE OF THE MOST IMPORTANT FEATURES.

The screenshots show multiple pipelines.

Examples visible include pipelines for:

- Website leads
- Manoj customers
- India MART
- White Label / Meta Ads
- Tiruppur Factory
- Direct Parties
- E-Commerce
- Retail sales
- other business-specific pipelines

The key concept is:

PIPELINES ARE CONFIGURABLE.

A pipeline contains:

Pipeline
  ↓
Ordered Stages

Different business channels can have different workflows.

Implement this concept if my system does not already have it.

Pipeline should support:

- name
- description if useful
- active/inactive
- ordered stages
- stage name
- stage order
- stage color/icon if appropriate
- probability if useful
- entry/exit behavior if appropriate
- permissions if needed

Avoid hardcoding one universal sales pipeline.

============================================================
F. CONTACT-SPECIFIC PIPELINE VISUALIZATION
============================================================

THIS IS A VERY IMPORTANT PROLEEDS CONCEPT.

The screenshots show a Contact Information view containing:

FOLLOW UPS
NOTES
PIPELINES & STAGES
CONTACT
OPPORTUNITY

The contact can belong to multiple pipelines.

Example:

Contact
 ├── India MART Pipeline
 │    ├── New Lead
 │    ├── Introduction Call
 │    ├── Catalog Sent
 │    ├── Follow-up
 │    ├── Quotation
 │    ├── Negotiation
 │    ├── Meeting
 │    ├── Sample
 │    ├── Payment
 │    ├── Dispatch
 │    └── Lost
 │
 └── White Label Pipeline
      ├── New Lead
      ├── Lookbook Sent
      ├── Price Quotation
      ├── Follow-up
      ├── Negotiation
      ├── Sample Requested
      ├── Order / Advance
      ├── Production
      ├── Shipped
      └── Post-Sales Follow-up

THIS IDEA IS HIGH VALUE.

A customer/contact should be able to participate in different business processes without creating duplicate customer records.

Implement this through proper relationships.

Example architecture:

Contact
  ↓
ContactPipelineMembership
  ↓
Pipeline
  ↓
PipelineStage
  ↓
StageHistory

Potentially:

Contact
  ↓
Opportunity
  ↓
Pipeline
  ↓
Current Stage

depending on the existing architecture.

DO NOT blindly implement the above tables.

Inspect the existing schema first and integrate correctly.

------------------------------------------------------------
G. CONTACT 360
------------------------------------------------------------

The Contact Information screens show a very useful compact customer relationship view.

Create/improve a Customer/Contact 360 experience.

It should be able to expose:

CONTACT
- name
- phone
- email
- company
- location
- tags
- owner
- type
- status

ACTIVITY
- follow-ups
- calls
- meetings
- tasks
- notes

SALES
- opportunities
- quotations
- orders

PIPELINES
- pipeline memberships
- current stage
- stage history

COMMUNICATION
- emails
- WhatsApp
- Instagram/messages
- other connected channels

BUSINESS
- order history
- outstanding amounts
- production status where relevant

DOCUMENTS
- attachments
- quotations
- files

The customer should have a unified history.

============================================================
H. VISUAL PIPELINE / STAGE HISTORY
============================================================

Do NOT merely show:

Current Stage = Negotiation

Show the journey.

Example:

New Lead
   →
Introduction Call
   →
Catalog Sent
   →
Follow-up
   →
Quotation
   →
Negotiation
   →
Meeting
   →
Sample
   →
Order
   →
Production
   →
Dispatch

Clearly distinguish:

completed stages
current stage
future stages
skipped stages
lost/on-hold stages

Stage changes must be persisted.

Maintain stage history.

This becomes extremely valuable for management and analytics.

============================================================
I. FOLLOW-UP MANAGEMENT
============================================================

The screenshots show a dedicated Follow-up area.

Important concepts:

- all follow-ups
- due today
- upcoming
- overdue
- completed
- contact
- title
- description
- created date
- due date
- status
- owner
- search
- filters
- quick actions

Implement/improve:

FollowUp

with proper relationship to:

Contact
Opportunity
Pipeline
Stage
Owner
Task/activity

Avoid duplicate task/follow-up systems.

If an existing Task system can support follow-ups cleanly, extend it instead.

============================================================
J. NOTES
============================================================

Contacts can contain notes.

Implement/improve:

- notes
- author
- timestamp
- editing
- deletion permissions
- relationship to contact/opportunity/order where appropriate

Notes should appear inside Customer 360.

============================================================
K. WORKFLOW AUTOMATION
============================================================

THIS IS THE MOST IMPORTANT FUNCTIONAL AREA IN THE SCREENSHOTS.

Proleeds has a workflow automation system.

The screenshots show workflows such as:

- Sample Sending
- Call Not Attend
- Production and Shipping
- Order Confirmation
- Negotiation Pre Call
- Nurturing
- Post Catalog Follow-Up
- Look Book + Rate Sending

These workflows are triggered by CRM events.

Examples:

"When a contact's stage is changed in selected pipeline automation will trigger"

"When a contact is added to selected pipeline automation will trigger"

This is extremely useful.

My application should have a generic workflow engine.

============================================================
L. EVENT-BASED AUTOMATION
============================================================

Support a system conceptually like:

TRIGGER
  ↓
CONDITIONS
  ↓
ACTIONS
  ↓
DELAYS
  ↓
BRANCHING
  ↓
MORE ACTIONS

Possible triggers:

- Contact created
- Lead created
- Contact added to pipeline
- Stage changed
- Opportunity created
- Opportunity stage changed
- Quotation created
- Quotation accepted
- Order created
- Order status changed
- Follow-up due
- Follow-up overdue
- Task completed
- Customer created
- Payment received
- Dispatch completed

Do NOT implement every trigger immediately.

Build the architecture so additional triggers can be added safely.

============================================================
M. VISUAL WORKFLOW BUILDER
============================================================

The screenshots show a node-based workflow builder.

I want the equivalent concept, but better.

Example:

[Trigger: Stage Changed]
          |
          v
[Wait 24 Hours]
          |
          v
[Internal Notification]
          |
          v
[Wait 4 Days]
          |
          v
[WhatsApp Message]
          |
          v
[Condition]
       /     \
     YES      NO
      |        |
   [Task]   [Notify]

The workflow builder should support:

- trigger node
- action node
- delay/wait node
- condition node
- branch
- CRM update
- notification
- communication
- task creation
- assignment
- stage update
- tagging

Use a proper graph/node model.

Do not store an entire workflow as an unvalidated arbitrary JSON blob without proper validation/versioning.

============================================================
N. WORKFLOW ACTIONS
============================================================

The screenshots visibly demonstrate actions such as:

- WhatsApp message
- Internal notification
- Add/Update to CRM
- comments
- timed delays

Potential actions:

CREATE TASK
SEND INTERNAL NOTIFICATION
SEND EMAIL
SEND WHATSAPP
ADD TAG
REMOVE TAG
UPDATE CONTACT
UPDATE OPPORTUNITY
CHANGE PIPELINE STAGE
ASSIGN STAFF
ADD NOTE
ADD COMMENT
CREATE FOLLOW-UP
WAIT
CONDITION
WEBHOOK

Only enable integrations that actually exist/configure safely.

============================================================
O. WORKFLOW CONTROLS
============================================================

The screenshots show:

- Active/Paused
- Save
- Test Workflow
- schedule enable
- schedule disable
- allow re-entry
- specific time
- last saved
- workflow status
- total contacts
- completed
- execution information

Implement a robust workflow lifecycle:

DRAFT
ACTIVE
PAUSED
ARCHIVED

Support:

- versioning
- activation
- pause
- test mode
- execution history
- error handling
- retry
- audit trail
- re-entry policy

"Allow Re-entry" is particularly useful.

Define exactly what re-entry means.

Example:

A contact can enter the same workflow again only when:

- explicitly allowed
- previous execution completed
- cooldown elapsed

Do not accidentally send duplicate messages.

============================================================
P. WORKFLOW EXECUTION HISTORY
============================================================

Do not only show the workflow definition.

Track executions.

Example:

Workflow
  ↓
Execution
  ↓
Node executions

Store:

- contact
- workflow
- execution ID
- started at
- completed at
- current node
- status
- error
- retry count
- action result

This will make the automation engine debuggable.

============================================================
Q. TASKS + WORKSPACES
============================================================

The screenshots show a separate task/workspace system.

Important concepts:

- Workspace
- Projects
- My Tasks
- Team Members
- Favorites
- Recent
- Projects
- Sections
- List
- Board
- Calendar
- Reports
- Time Logs
- Add Task

The example workspace includes:

Tiruppur Factory
  ↓
Projects / sections
  ↓
Tasks

There are task examples such as:

Website
- All Section Updation with Relevant Fields
- Add Lead Magnets
- All Apps Linking
- Workflow Setups
- Auto Reply for Leads
- Auto Redirection to Website
- Auto Posting in All Apps

This demonstrates that tasks can exist independently while still belonging to a project/workspace.

If my existing task system is basic:

upgrade it.

============================================================
R. TASK STRUCTURE
============================================================

Consider:

Workspace
 ↓
Project
 ↓
Section
 ↓
Task
 ↓
Subtask

Task fields:

- title
- description
- status
- priority
- assignee
- watchers
- due date
- start date
- tags
- attachments
- comments
- related contact
- related opportunity
- related order
- related project
- time logs

Do not duplicate existing task entities.

============================================================
S. TASK VIEWS
============================================================

The screenshots show multiple ways to view work.

Support where useful:

LIST
BOARD
CALENDAR
REPORT

Potentially:

TABLE
KANBAN
TIMELINE

The underlying task data must be the same.

Views are representations of the same records.

============================================================
T. TIME LOGS
============================================================

The task system exposes Time Logs.

If my current system lacks it, consider implementing:

Task
 ↓
TimeEntry

with:

- employee
- task
- start
- end
- duration
- description

Useful for:

- productivity
- costing
- project management
- employee analytics

Only add if relevant to my business.

============================================================
U. UNIFIED INBOX
============================================================

The screenshots show a communication inbox.

It includes conversations and channels such as Instagram and WhatsApp.

Important concepts:

- conversation list
- search conversations
- unread
- starred
- all
- groups
- channel indicator
- message history
- message composer
- attachments/media if supported
- contact association

This should become a unified communication layer.

============================================================
V. OMNICHANNEL CONTACT LINKING
============================================================

A conversation should resolve to a CRM contact whenever possible.

Example:

WhatsApp number
   ↓
Contact

Instagram account
   ↓
Contact

Email
   ↓
Contact

Then:

Contact
 └── Communications
       ├── WhatsApp
       ├── Instagram
       ├── Email
       └── Other channels

Do not create duplicate customers because the same person contacts the company through another channel.

============================================================
W. CALENDAR
============================================================

The screenshots show:

- monthly calendar
- all calendars
- booked
- cancelled
- show up
- no show
- rescheduled
- appointments

Implement/improve calendar functionality around:

Meetings
Appointments
Follow-ups
Tasks
Sales calls

Each appointment should be linked to:

- contact
- opportunity
- owner
- date/time
- status
- notes

============================================================
X. STAFF / TEAM MANAGEMENT
============================================================

The screenshots show Staff management.

Important concepts:

- staff
- email
- phone
- profile
- role/permission relationship

Integrate with my existing:

Users
Roles
Permissions
Teams

Do NOT create another user system.

============================================================
Y. TAGS
============================================================

Proleeds has configurable Tags.

Tags should be reusable across:

- contacts
- leads
- opportunities
- customers
- tasks
- projects
- conversations

Use a relational many-to-many design where appropriate.

Support:

- create
- rename
- color
- archive
- search/filter

Avoid hardcoded tag lists.

============================================================
Z. CUSTOM FIELDS
============================================================

The screenshots show configurable Fields / Values.

This indicates a customizable CRM data model.

Investigate whether my application should support custom fields.

Potentially:

Entity
+
Custom Field Definition
+
Custom Field Value

For:

Contact
Opportunity
Lead
Customer
Task

But:

DO NOT replace strongly typed core business fields with custom fields.

Use custom fields for business-specific extension.

Example:

Contact custom field:
Preferred Garment Category

Opportunity custom field:
Buyer Type

Customer custom field:
Annual Purchase Potential

============================================================
AA. DOMAIN / BUSINESS CONFIGURATION
============================================================

The screenshots show:

Domain Settings
DNS verification
domain options
SMTP configuration

Extract only relevant concepts.

My application should eventually support:

- company domain
- email sending configuration
- SMTP/provider configuration
- domain verification
- sender identity

Security is critical.

Never expose SMTP passwords/secrets in frontend responses.

============================================================
AB. FILE / MEDIA VAULT
============================================================

The screenshots show a file manager / vault.

Capabilities visible include:

- folders
- files
- images
- video
- documents
- audio
- search
- sorting
- storage usage
- file metadata
- project folders

This is potentially useful for my CRM/ERP.

Consider a central document/file system.

Example:

Customer
 └── Documents

Opportunity
 └── Documents

Quotation
 └── Documents

Order
 └── Documents

Production Lot
 └── Documents

Do not duplicate storage implementations.

============================================================
AC. INTEGRATIONS
============================================================

The screenshots show integrations/connections such as:

Facebook
Instagram
LLM provider
Pabbly

Extract the underlying idea:

A centralized integrations page.

My application should eventually provide:

Integration
Provider
Connection Status
Configuration
Permissions
Disconnect
Reconnect
Test Connection

Potential future integrations:

WhatsApp
Email
Instagram
Facebook
Google Calendar
Google Drive
Accounting/GST
Payment gateway
LLM provider
Webhooks

Only implement providers we actually intend to support.

============================================================
AD. LLM / AI CONNECTION
============================================================

The screenshots include connecting an LLM provider.

For MY system:

AI should sit ABOVE the CRM/ERP.

Do NOT give an LLM unrestricted PostgreSQL access.

Architecture should be:

User
 ↓
AI Orchestrator
 ↓
Approved Tools
 ↓
CRM/ERP Services
 ↓
Database

AI can:

- search
- summarize
- explain
- recommend
- draft
- classify
- trigger approved actions

Business calculations remain deterministic.

============================================================
AE. NOTIFICATIONS
============================================================

The settings area exposes Notifications.

Create/improve a centralized notification architecture.

Notifications can originate from:

- workflow
- task
- follow-up
- assignment
- approval
- overdue activity
- order
- production milestone

Support:

- in-app
- email
- WhatsApp where configured

Do not create separate notification implementations for every module.

============================================================
AF. RECOVERY / BACKUP
============================================================

The settings show a Recover capability.

Investigate what recovery functionality makes sense for my application.

At minimum:

- auditability
- backup strategy
- restore strategy
- data recovery
- soft delete where appropriate

Never implement destructive "restore" functionality without safeguards.

============================================================
AG. REPORTING
============================================================

The dashboards and list views imply reporting.

Build reporting around actual business data.

Potential CRM reports:

Lead conversion
Pipeline value
Stage conversion
Salesperson performance
Follow-up performance
Overdue follow-ups
Opportunity ageing
Lost reasons
Customer acquisition
Customer activity

ERP reports remain separate but interconnected.

============================================================
AH. SEARCH + FILTERS
============================================================

The screenshots repeatedly show:

Search
Status filters
Date filters
Latest first
Folder
Workflow
Rows per page

This is important.

Standardize a reusable search/filter framework.

Where applicable:

- search
- filtering
- sorting
- pagination
- saved views
- column selection
- export
- bulk actions

Do not build these separately from scratch for every module.

============================================================
AI. CRM WORKFLOW + ERP WORKFLOW CONNECTION
============================================================

This is where MY application should become substantially better.

Example:

Customer
 ↓
Opportunity
 ↓
Quotation
 ↓
Order
 ↓
Style
 ↓
Lot
 ↓
Production
 ↓
Packing
 ↓
Dispatch
 ↓
Invoice
 ↓
Payment

CRM users should see relevant ERP status.

ERP users should see relevant customer/order context.

But maintain clear module boundaries.

============================================================
AJ. APPAREL-SPECIFIC PIPELINES
============================================================

Do not hardcode Proleeds' pipelines.

Create configurable pipelines suitable for my business.

Potential examples:

WHOLESALE BUYER

New Enquiry
→ Qualification
→ Requirements
→ Catalog Sent
→ Price Discussion
→ Quotation
→ Negotiation
→ Sample
→ Approval
→ Order
→ Production
→ Dispatch
→ Payment
→ Post-Sales

WHITE LABEL

New Lead
→ Brand Discussion
→ Requirements
→ Design
→ Sample
→ Sample Approval
→ Costing
→ Quotation
→ Order
→ Production
→ QC
→ Dispatch
→ Post-Sales

EXPORT BUYER

Enquiry
→ Qualification
→ Tech Pack
→ Costing
→ Sample
→ Approval
→ PO
→ Production
→ Inspection
→ Packing
→ Shipment
→ Payment

IMPORTANT:

These are examples only.

Use my existing business requirements and configurable pipeline architecture.

Do NOT hardcode these pipelines into the database.

============================================================
AK. ERP TRACEABILITY
============================================================

The CRM pipeline must not replace manufacturing workflows.

They should connect.

Example:

CRM:

Customer
 ↓
Opportunity
 ↓
Quotation
 ↓
Order

ERP:

Order
 ↓
Style
 ↓
Lot
 ↓
Fabric
 ↓
Production
 ↓
Packing
 ↓
Dispatch

CRM can display:

Order
Production: 72%
Expected Dispatch: DATE
Current Stage: Sewing
QC: Pending

while the production module handles the detailed operations.

============================================================
AL. UI / UX
============================================================

Use the functional lessons from Proleeds but DO NOT copy its UI.

My application should feel:

Premium
Modern
Fast
Professional
Dense where necessary
Visually clear
Highly interactive

Use:

- cards
- tables
- kanban
- timelines
- relationship panels
- breadcrumbs
- drawers
- modals
- contextual actions
- visual pipelines
- workflow graphs
- command/search interfaces

Avoid unnecessary decoration.

============================================================
AM. HIERARCHICAL NAVIGATION
============================================================

This is a major product direction.

Users should be able to move naturally:

Customer
 ↓
Contact
 ↓
Opportunity
 ↓
Quotation
 ↓
Order
 ↓
Style
 ↓
Lot
 ↓
Production

And:

Order
 ↓
Materials
 ↓
Fabric
 ↓
Production
 ↓
Packing
 ↓
Dispatch

Provide:

- breadcrumbs
- relationship panels
- linked records
- "open related"
- contextual actions
- parent/child navigation

No dead-end pages.

============================================================
AN. AUDIT TRAIL
============================================================

Important CRM events should be auditable.

Track:

- created
- edited
- assigned
- stage changed
- pipeline changed
- status changed
- quotation created
- order created
- workflow triggered
- task completed
- communication sent

Do not store audit data only in frontend state.

============================================================
AO. PERMISSIONS
============================================================

Every new capability must respect:

User
Role
Permission
Team
Ownership

Examples:

Salesperson
Manager
Production
Finance
Admin

A salesperson may see their customers.

Manager may see team customers.

Finance may see financial information.

Production may see production information.

Admin has broader access.

Use existing RBAC architecture.

============================================================
AP. DATABASE PRINCIPLES
============================================================

Before adding tables:

inspect existing schema.

Reuse existing entities.

Avoid duplicate concepts.

Use:

- foreign keys
- indexes
- unique constraints
- timestamps
- soft deletion where appropriate
- audit fields
- proper many-to-many relationships
- transactional integrity

All schema changes require migrations.

Never modify production schema manually without migration support.

============================================================
AQ. BACKEND ARCHITECTURE
============================================================

Business logic must live in services/domain layers.

Do not place critical business rules inside React.

Do not allow the AI model to calculate:

- stock
- GST
- totals
- outstanding
- profit
- inventory balances

Those remain deterministic backend services.

============================================================
AR. API DESIGN
============================================================

Create consistent APIs.

Examples conceptually:

/pipelines
/pipelines/{id}/stages
/contacts/{id}/pipelines
/contacts/{id}/timeline
/contacts/{id}/activities
/contacts/{id}/notes
/opportunities
/follow-ups
/workflows
/workflows/{id}/versions
/workflows/{id}/executions
/tasks
/projects
/workspaces
/calendar
/conversations
/integrations
/notifications

BUT:

Do not create these exact endpoints if equivalent APIs already exist.

Extend existing APIs.

============================================================
AS. FRONTEND COMPONENT SYSTEM
============================================================

Create reusable components where appropriate:

PipelineBoard
PipelineStage
Contact360
RelationshipTimeline
ActivityTimeline
FollowUpList
WorkflowCanvas
WorkflowNode
WorkflowExecutionPanel
TaskBoard
TaskList
CalendarView
ConversationInbox
IntegrationCard
NotificationCenter
GlobalSearch
FilterBar
SavedView

Do not duplicate UI logic across modules.

============================================================
AT. WORKFLOW ENGINE SAFETY
============================================================

Critical.

Automation must be safe.

Implement:

- idempotency
- retries
- execution locking
- duplicate prevention
- re-entry controls
- execution logs
- failure states
- timeouts
- permission checks
- rate limiting where required

For external messages:

Never accidentally send the same WhatsApp/email multiple times because of a retry.

============================================================
AU. TESTING
============================================================

For every implemented capability create tests.

At minimum:

DATABASE
- migration
- constraints
- relationships

BACKEND
- CRUD
- permissions
- validation
- business rules

WORKFLOW
- trigger
- action
- delay
- branch
- retry
- re-entry
- failure

CRM
- contact
- opportunity
- pipeline
- stage history
- follow-up
- timeline

FRONTEND
- critical flows
- forms
- pipeline movement
- workflow builder
- task creation

REGRESSION
- existing CRM
- existing ERP

============================================================
AVOID OVERENGINEERING
============================================================

Do not implement every feature simply because Proleeds has it.

Every proposed feature must answer:

1. Does it solve a real problem?
2. Is it missing from my application?
3. Does it integrate naturally?
4. Is it worth the complexity?
5. Will users actually use it?

If not:

IGNORE IT.

============================================================
IMPLEMENTATION ORDER
============================================================

Implement in this order:

PHASE 1
Proleeds audit + existing-system audit

PHASE 2
CRM relationships / Customer 360

PHASE 3
Configurable pipelines + stage history

PHASE 4
Follow-ups + activities + timeline

PHASE 5
Workflow automation engine

PHASE 6
Visual workflow builder

PHASE 7
Workflow execution/history/re-entry

PHASE 8
Tasks + projects + workspaces

PHASE 9
Calendar + appointments

PHASE 10
Unified communication inbox

PHASE 11
Tags + custom fields

PHASE 12
Files/documents/vault

PHASE 13
Integrations

PHASE 14
Notifications

PHASE 15
Dashboard/reporting

PHASE 16
CRM ↔ ERP relationship layer

PHASE 17
AI orchestration

PHASE 18
Security + testing + production hardening

============================================================
IMPORTANT IMPLEMENTATION RULE
============================================================

Do NOT implement all phases in one uncontrolled change.

At the end of each phase:

1. show what you changed
2. show database migrations
3. show APIs added/modified
4. show frontend changes
5. show tests
6. show any risks
7. verify existing functionality
8. update:

/docs/PROLEEDS_FEATURE_AUDIT.md

and

/docs/ERP_UPGRADE_PROGRESS.md

============================================================
FINAL PRODUCT VISION
============================================================

The final application should feel like:

A premium CRM at the front

+
A serious ERP underneath

+
A configurable workflow engine

+
A Customer 360 relationship platform

+
An operational command center

+

AI on top of everything.

The most important relationship is:

CUSTOMER
 ↓
CONTACT
 ↓
OPPORTUNITY
 ↓
PIPELINE
 ↓
STAGE
 ↓
QUOTATION
 ↓
ORDER
 ↓
STYLE
 ↓
LOT
 ↓
PRODUCTION
 ↓
DISPATCH
 ↓
INVOICE
 ↓
PAYMENT

And every important event should be:

SEARCHABLE
TRACEABLE
AUDITABLE
AUTOMATABLE
CONNECTED

============================================================
FINAL RULE
============================================================

Do not say:

"Proleeds has this, therefore we need it."

Instead say:

"Proleeds demonstrates this capability. Here is the business value. Here is how our existing system handles it. Here is why we should or should not add it."

Build a BETTER PRODUCT, not a clone.