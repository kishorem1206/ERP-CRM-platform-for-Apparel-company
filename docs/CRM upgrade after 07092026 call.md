# CRM Enhancement — Lead Management, Employee Tasks, Platform Analytics & WhatsApp Automation

We already have an existing CRM & ERP application. **Do not rebuild the existing system from scratch.** Extend the current architecture, UI, database, APIs, and workflows to add the following CRM capabilities.

Before making changes, inspect the existing frontend, backend, database schema, authentication/roles, lead/customer modules, notification system, and existing UI patterns. Reuse existing components and architecture wherever possible.

The goal is to make the CRM suitable for an apparel manufacturing/business company where leads come from multiple platforms and are handled by company employees through structured follow-ups and sales activities.

---

## PHASE 1 — Lead Assignment to Employees

Add the ability to assign every lead to a specific company employee.

### Requirements

- Every lead should have:
  - Lead owner / assigned employee
  - Assigned date
  - Assigned by
  - Assignment status
- Admin/manager should be able to:
  - Assign a lead
  - Reassign a lead
  - View all leads assigned to an employee
  - Filter leads by employee
- Employees should see:
  - Leads assigned to them
  - Priority
  - Lead status
  - Next follow-up
  - Last interaction
  - Pending tasks

### UI

Add an intuitive assignment control inside the lead detail page.

Example:

Lead → Assigned To → Employee → Current Status → Next Follow-up

Also provide employee-wise filtering in the lead list.

---

# PHASE 2 — Lead Follow-Up Management

Build a proper follow-up workflow instead of relying on manual notes.

Every lead should support:

- Next follow-up date
- Next follow-up time
- Follow-up type
- Follow-up reason
- Follow-up notes
- Follow-up status
- Last contacted date
- Contact outcome
- Next action

### Follow-up types

Support configurable types such as:

- WhatsApp
- Phone call
- Email
- Meeting
- Catalogue sent
- Quotation sent
- Sample sent
- Price discussion
- Payment discussion
- Other

### Follow-up lifecycle

Lead created  
→ Assigned  
→ Contacted  
→ Follow-up scheduled  
→ Follow-up completed  
→ Next follow-up scheduled  
→ Converted / Lost / On Hold

The system should make the **next action obvious** to the employee.

---

# PHASE 3 — Employee To-Do / Task System

Create a centralized task system connected to leads.

Employees should have a "My Tasks / To-Do" section.

Tasks can originate from:

- Lead creation
- Lead assignment
- Follow-up scheduling
- Missed follow-up
- Catalogue sharing
- Quotation
- Sample request
- Customer request
- Manager assignment
- Automated workflow

Each task should contain:

- Task title
- Related lead
- Related company/customer
- Assigned employee
- Due date
- Due time
- Priority
- Status
- Notes
- Created by
- Completed date

### Task statuses

- Pending
- In Progress
- Completed
- Overdue
- Cancelled

### Dashboard

Employee dashboard should prominently show:

**Today's Tasks**

**Overdue Tasks**

**Upcoming Follow-ups**

**Leads Requiring Action**

**Completed Today**

Managers should additionally be able to see employee-wise task performance.

---

# PHASE 4 — Platform-Wise Lead Analytics

Track where every lead originated.

Examples:

- WhatsApp
- Instagram
- Facebook
- Website
- IndiaMART
- Trade show
- Referral
- Google
- Direct
- Other

Every lead should have:

`Lead Source / Platform`

Do not hard-code this unnecessarily. Make it configurable.

### Reports

Create platform-wise reports showing:

- Number of leads
- Qualified leads
- Converted leads
- Lost leads
- Conversion rate
- Revenue generated
- Average lead value
- Cost per lead
- Cost per conversion
- Total advertising spend
- ROI / ROAS where sufficient data exists

Allow filtering by:

- Date
- Platform
- Employee
- Lead status
- Product/category
- Customer

---

# PHASE 5 — Lead Spending / Acquisition Cost

Add the ability to record money spent to acquire leads.

Track:

- Platform
- Campaign
- Ad spend
- Date/date range
- Number of leads generated
- Qualified leads
- Converted leads
- Revenue generated

Calculate:

### Cost Per Lead

Ad Spend / Number of Leads

### Cost Per Qualified Lead

Ad Spend / Qualified Leads

### Cost Per Conversion

Ad Spend / Converted Leads

### ROAS

Revenue Attributed to Campaign / Ad Spend

The system must clearly distinguish between:

**Actual recorded values**

and

**Calculated metrics**

Do not create fake analytics where insufficient data exists.

---

# PHASE 6 — Ad Spend Management

Create an **Ad Spend** section under CRM analytics.

Allow authorized users to enter/import:

- Platform
- Campaign
- Campaign ID
- Ad set
- Date
- Spend
- Impressions
- Clicks
- Leads
- Qualified leads
- Conversions
- Revenue

Support manual entry initially, while keeping the architecture extensible for future API integrations with advertising platforms.

Dashboard should provide:

- Total spend
- Spend by platform
- Spend by campaign
- Leads generated
- Cost per lead
- Conversions
- Cost per conversion
- Revenue
- ROAS

---

# PHASE 7 — Catalogue & Activity-Based Pricing

Add catalogue/product pricing functionality connected to CRM activities.

The system should allow the company to maintain:

- Product/catalogue
- Product SKU
- Product category
- Catalogue price
- Customer-specific price where applicable
- Minimum quantity
- Applicable date
- Price history

Pricing should be usable during CRM activities such as:

Lead enquiry  
→ Product selected  
→ Catalogue/product shared  
→ Price shown  
→ Quotation created

Do not duplicate product master data if the ERP already contains the relevant Product/SKU master.

The CRM should reference the existing product/SKU records.

---

# PHASE 8 — WhatsApp Integration & Automated Communication

Design the CRM so WhatsApp communication can be integrated into the lead workflow.

The objective is to automatically send relevant messages at the appropriate stage.

Examples:

### New Lead

Lead created  
→ Assign employee  
→ Send acknowledgement where appropriate

### Catalogue

Employee selects catalogue/product  
→ Send relevant catalogue/message

### Follow-Up

Follow-up becomes due  
→ Send configured reminder/message where appropriate

### Quotation

Quotation generated  
→ Send quotation notification/message

### Sample

Sample dispatched  
→ Send notification

### Reminder

Follow-up due  
→ Notify employee and/or customer depending on configured workflow

### Important

Do not hard-code messages directly into business logic.

Create configurable:

- Message templates
- Trigger
- Recipient
- Timing
- Variables
- Enable/disable setting

Example variables:

`{{customer_name}}`

`{{company_name}}`

`{{employee_name}}`

`{{product_name}}`

`{{quotation_number}}`

`{{followup_date}}`

`{{order_number}}`

The WhatsApp layer should be implemented in a way that can support an official WhatsApp Business API/provider later.

Do not use unofficial WhatsApp automation that could create account/compliance problems.

---

# PHASE 9 — CRM Automation Engine

Introduce a lightweight workflow/automation layer.

The system should be able to execute:

**Trigger → Condition → Action**

Example:

Lead Created  
→ Source = Instagram  
→ Assign to Sales Employee A

Another:

Lead Status = "Quotation Sent"  
→ Follow-up after 2 days  
→ Create employee task

Another:

Follow-up Due  
→ Create overdue task  
→ Notify employee

Another:

Lead Converted  
→ Create customer  
→ Connect customer to ERP/customer master

Another:

Catalogue Sent  
→ Schedule follow-up

Make these rules configurable wherever practical.

---

# PHASE 10 — CRM Dashboard

Create a modern CRM dashboard focused on actionable information.

### KPI cards

- Total Leads
- New Leads
- Qualified Leads
- Follow-ups Today
- Overdue Follow-ups
- Converted Leads
- Conversion Rate
- Revenue
- Ad Spend
- Cost per Lead

### Visual sections

- Lead funnel
- Leads by platform
- Leads by employee
- Conversion trend
- Ad spend trend
- Revenue by platform
- Follow-up performance
- Pending employee tasks

The dashboard should allow clicking a metric to drill into the underlying leads/tasks.

---

# PHASE 11 — Notifications

Introduce a unified notification system.

Notify employees for:

- New lead assigned
- Lead reassigned
- Follow-up due
- Follow-up overdue
- New task
- Task approaching deadline
- Customer response
- Important CRM activity

Managers can receive:

- Overdue follow-up summaries
- Employee task summaries
- Lead conversion summaries
- Campaign performance summaries

Avoid excessive notifications. Notifications should be configurable.

---

# PHASE 12 — Database & Backend Changes

Do not merely implement this visually.

Update the actual backend and database.

Review the existing schema and add appropriate entities/relationships for:

- Leads
- Lead assignments
- Lead sources/platforms
- Follow-ups
- Tasks
- Ad campaigns
- Ad spend
- Lead acquisition costs
- Catalogue/product references
- Price history
- Communication logs
- WhatsApp message templates
- Automation rules
- Notifications

Use proper foreign keys and relationships.

Avoid duplicating existing:

- Users/employees
- Customers/companies
- Products/SKUs
- Orders
- Quotations

Reuse existing entities wherever they already exist.

---

# PHASE 13 — Frontend Integration

Integrate everything into the **existing CRM design**.

Do not create a disconnected second CRM.

Existing navigation, typography, colors, cards, tables, modals, forms, permissions, and interaction patterns should remain consistent.

Add or enhance:

- Lead list
- Lead detail
- Employee assignment
- Follow-up timeline
- My Tasks
- Team Tasks
- CRM dashboard
- Platform analytics
- Ad spend
- Catalogue/pricing
- Communication history
- Automation settings

Lead detail should become the central workspace.

Suggested structure:

Lead Header  
↓  
Customer / Company Information  
↓  
Lead Status + Owner  
↓  
Products / Catalogue  
↓  
Activity Timeline  
↓  
Follow-ups  
↓  
Tasks  
↓  
Communication History  
↓  
Quotation / Commercial Information  
↓  
Related ERP Records

---

# PHASE 14 — Permissions & Roles

Respect the existing authentication/authorization system.

Typical permissions:

### Admin

Full access.

### Manager

- View team leads
- Assign/reassign leads
- View analytics
- Manage campaigns
- View employee performance

### Sales Employee

- View assigned leads
- Update leads
- Create follow-ups
- Complete tasks
- Send approved communications

### Other Employees

Only access the CRM information relevant to their role.

Do not expose sensitive commercial/employee information unnecessarily.

---

# PHASE 15 — End-to-End Testing

After implementation, test complete real-world workflows.

### Workflow 1 — New Lead

Lead arrives  
→ Lead created  
→ Platform recorded  
→ Employee assigned  
→ Employee notified  
→ Follow-up task created  
→ Employee contacts lead  
→ Activity recorded  
→ Next follow-up scheduled

### Workflow 2 — Catalogue

Lead enquiry  
→ Product selected  
→ Catalogue/pricing retrieved  
→ Catalogue sent  
→ Activity logged  
→ Follow-up automatically scheduled

### Workflow 3 — Advertisement

Campaign created  
→ Ad spend recorded  
→ Leads attributed to platform/campaign  
→ Conversion tracked  
→ Revenue attributed  
→ CPL / CPA / ROAS calculated

### Workflow 4 — Follow-Up

Follow-up scheduled  
→ Employee sees task  
→ Reminder generated  
→ Employee completes follow-up  
→ Notes recorded  
→ Next follow-up scheduled

### Workflow 5 — Conversion

Lead converted  
→ Customer/company created or linked  
→ Product/order/quotation information linked  
→ CRM history retained  
→ ERP workflow can continue without duplicate data entry.

---

# IMPORTANT IMPLEMENTATION RULES

1. **Inspect the existing application before changing anything.**

2. Do not rebuild existing functionality that already works.

3. Do not create duplicate database entities when an existing entity can be reused.

4. Changes must work across:
   - Database
   - Backend/API
   - Frontend
   - Authentication
   - Permissions
   - Notifications
   - Reports

5. Do not implement features as frontend-only mockups.

6. All important CRM actions must persist to the database.

7. Existing ERP functionality must continue working.

8. Maintain backward compatibility with existing data.

9. Add migrations for database changes.

10. Add validation and error handling.

11. Use realistic seed/demo data only where necessary for development/testing.

12. Keep the architecture modular so WhatsApp, advertising platforms, email, and other integrations can be added later.

13. Do not invent external API integrations if credentials/API access are not available. Build the integration layer/interface and clearly identify what requires external credentials.

14. After each phase, test the feature before moving to the next phase.

15. At the end of each phase, provide:
   - What was changed
   - Database changes
   - Backend changes
   - Frontend changes
   - API endpoints added/modified
   - Files changed
   - Tests performed
   - Any remaining limitations

# FINAL OBJECTIVE

Transform the existing CRM into an **action-oriented apparel business CRM** where:

**Lead → Assignment → Follow-up → Employee Task → Catalogue/Product → Communication → Quotation → Conversion → Customer → ERP**

is one connected workflow.

The system should not simply store leads. It should actively help employees know **what to do next**, help managers understand **where leads and money are coming from**, and connect CRM activities with the existing ERP/customer/product data.