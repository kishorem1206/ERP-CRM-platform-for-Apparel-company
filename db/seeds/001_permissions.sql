-- Seed: all system permissions
INSERT INTO permissions (id, code, description) VALUES
-- Master Data
(uuid_generate_v4(), 'master_data.view',   'View master data'),
(uuid_generate_v4(), 'master_data.create', 'Create master records'),
(uuid_generate_v4(), 'master_data.edit',   'Edit master records'),
(uuid_generate_v4(), 'master_data.delete', 'Delete master records'),
-- CRM
(uuid_generate_v4(), 'crm.view',   'View CRM data'),
(uuid_generate_v4(), 'crm.create', 'Create leads and activities'),
(uuid_generate_v4(), 'crm.edit',   'Edit CRM records'),
(uuid_generate_v4(), 'crm.delete', 'Delete CRM records'),
-- Quotation
(uuid_generate_v4(), 'quotation.view',    'View quotations'),
(uuid_generate_v4(), 'quotation.create',  'Create quotations'),
(uuid_generate_v4(), 'quotation.approve', 'Approve quotations'),
(uuid_generate_v4(), 'quotation.cancel',  'Cancel quotations'),
-- Sales Order
(uuid_generate_v4(), 'sales_order.view',    'View sales orders'),
(uuid_generate_v4(), 'sales_order.create',  'Create sales orders'),
(uuid_generate_v4(), 'sales_order.approve', 'Approve sales orders'),
(uuid_generate_v4(), 'sales_order.cancel',  'Cancel sales orders'),
-- Delivery
(uuid_generate_v4(), 'delivery.view',     'View deliveries'),
(uuid_generate_v4(), 'delivery.create',   'Create delivery notes'),
(uuid_generate_v4(), 'delivery.dispatch', 'Mark deliveries dispatched'),
-- Invoice
(uuid_generate_v4(), 'invoice.view',   'View invoices'),
(uuid_generate_v4(), 'invoice.create', 'Create invoices'),
(uuid_generate_v4(), 'invoice.cancel', 'Cancel invoices'),
-- Purchase
(uuid_generate_v4(), 'purchase_order.view',    'View purchase orders'),
(uuid_generate_v4(), 'purchase_order.create',  'Create purchase orders'),
(uuid_generate_v4(), 'purchase_order.approve', 'Approve purchase orders'),
(uuid_generate_v4(), 'purchase_order.cancel',  'Cancel purchase orders'),
(uuid_generate_v4(), 'purchase_entry.view',    'View purchase entries'),
(uuid_generate_v4(), 'purchase_entry.create',  'Create purchase entries'),
(uuid_generate_v4(), 'purchase_return.view',   'View purchase returns'),
(uuid_generate_v4(), 'purchase_return.create', 'Create purchase returns'),
-- Inventory
(uuid_generate_v4(), 'inventory.view',            'View stock and transactions'),
(uuid_generate_v4(), 'inventory.receive',          'Receive stock'),
(uuid_generate_v4(), 'inventory.issue',            'Issue stock'),
(uuid_generate_v4(), 'inventory.transfer',         'Transfer stock between warehouses'),
(uuid_generate_v4(), 'inventory.adjust',           'Adjust stock'),
(uuid_generate_v4(), 'inventory.opening_balance',  'Set opening balances'),
-- Production
(uuid_generate_v4(), 'production.view',     'View production lots'),
(uuid_generate_v4(), 'production.create',   'Create production lots'),
(uuid_generate_v4(), 'production.start',    'Start production'),
(uuid_generate_v4(), 'production.log',      'Log production entries'),
(uuid_generate_v4(), 'production.complete', 'Complete/close lots'),
(uuid_generate_v4(), 'production.cancel',   'Cancel lots'),
-- Finance
(uuid_generate_v4(), 'finance.view',    'View financial records'),
(uuid_generate_v4(), 'finance.receipt', 'Record customer receipts'),
(uuid_generate_v4(), 'finance.payment', 'Record vendor payments'),
(uuid_generate_v4(), 'finance.expense', 'Record expenses'),
-- Reports
(uuid_generate_v4(), 'reports.sales',       'View sales reports'),
(uuid_generate_v4(), 'reports.purchase',    'View purchase reports'),
(uuid_generate_v4(), 'reports.inventory',   'View inventory reports'),
(uuid_generate_v4(), 'reports.production',  'View production reports'),
(uuid_generate_v4(), 'reports.finance',     'View financial reports'),
(uuid_generate_v4(), 'reports.gst',         'View GST reports'),
-- Admin
(uuid_generate_v4(), 'admin.users',    'Manage users'),
(uuid_generate_v4(), 'admin.roles',    'Manage roles and permissions'),
(uuid_generate_v4(), 'admin.settings', 'Manage company settings'),
(uuid_generate_v4(), 'admin.audit',    'View audit logs')
ON CONFLICT (code) DO NOTHING;
