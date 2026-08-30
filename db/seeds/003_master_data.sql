-- =============================================================
-- Phase 0: Master Data Foundation
-- Run AFTER 001_permissions.sql and 002_hsn_codes.sql
-- Company ID is resolved dynamically via subquery.
-- =============================================================

-- Additional HSN codes needed for apparel raw materials & packing
INSERT INTO hsn_codes (hsn, description, gst_rate) VALUES
('3923', 'BOPP bags and plastics articles for packing', 18.00),
('4819', 'Cartons, boxes, cases of paper or paperboard', 18.00),
('4823', 'Other articles of paper — inner cards, stiffeners', 18.00),
('9606', 'Buttons, press-fasteners, snap-fasteners, studs', 12.00)
ON CONFLICT (hsn) DO NOTHING;

-- =============================================================
-- CATEGORIES
-- =============================================================
INSERT INTO categories (id, company_id, name)
SELECT gen_random_uuid(), c.id, v.name
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('Yarn'),
    ('Fabric'),
    ('Trim'),
    ('Packing Material'),
    ('Finished Goods')
) v(name)
ON CONFLICT (company_id, name) DO NOTHING;

-- =============================================================
-- SUB-CATEGORIES
-- =============================================================
INSERT INTO sub_categories (id, company_id, category_id, name)
SELECT gen_random_uuid(), c.id, cat.id, v.sub
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('Yarn',             'Viscose Lycra Yarn'),
    ('Yarn',             'Ring Lycra Yarn'),
    ('Fabric',           'Single Jersey'),
    ('Fabric',           'Double Jersey'),
    ('Fabric',           'Rib Fabric'),
    ('Trim',             'Buttons'),
    ('Trim',             'Elastic'),
    ('Trim',             'Zipper'),
    ('Trim',             'Label'),
    ('Packing Material', 'Inner Card'),
    ('Packing Material', 'Poly Bag'),
    ('Packing Material', 'Carton')
) v(cat_name, sub)
JOIN categories cat ON cat.company_id = c.id AND cat.name = v.cat_name;

-- =============================================================
-- COLOURS
-- =============================================================
INSERT INTO colours (id, company_id, name, hex_code)
SELECT gen_random_uuid(), c.id, v.name, v.hex
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('White',       '#FFFFFF'),
    ('Black',       '#000000'),
    ('Pink',        '#FFC0CB'),
    ('Navy Blue',   '#001F5B'),
    ('Red',         '#CC0000'),
    ('Grey',        '#808080'),
    ('Brown',       '#795548'),
    ('Yellow',      '#FFEB3B'),
    ('Green',       '#2E7D32'),
    ('Orange',      '#E65100')
) v(name, hex)
ON CONFLICT (company_id, name) DO NOTHING;

-- =============================================================
-- SIZES  (adult sizes + infant sizes)
-- =============================================================
INSERT INTO sizes (id, company_id, name, sort_order)
SELECT gen_random_uuid(), c.id, v.name, v.ord
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('XS',   1),
    ('S',    2),
    ('M',    3),
    ('L',    4),
    ('XL',   5),
    ('XXL',  6),
    ('XXXL', 7),
    ('3M',   10),
    ('6M',   11),
    ('9M',   12),
    ('12M',  13),
    ('18M',  14),
    ('24M',  15)
) v(name, ord)
ON CONFLICT (company_id, name) DO NOTHING;

-- =============================================================
-- ADDITIONAL WAREHOUSES
-- (Main Warehouse already created by seed.py)
-- =============================================================
INSERT INTO warehouses (id, company_id, name, code, is_active)
SELECT gen_random_uuid(), c.id, v.name, v.code, true
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('Yarn Store',          'WH-YARN'),
    ('Fabric Store',        'WH-FAB'),
    ('Trim Store',          'WH-TRIM'),
    ('Packing Store',       'WH-PACK'),
    ('Finished Goods Store','WH-FG'),
    ('Rejection Store',     'WH-REJ')
) v(name, code)
ON CONFLICT (company_id, code) DO NOTHING;

-- =============================================================
-- DOCUMENT SEQUENCES
-- =============================================================
INSERT INTO document_sequences (company_id, document_type, prefix, separator, year_format, next_number, padding)
SELECT c.id, v.doc_type, v.prefix, '/', 'YY', 1, 4
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('purchase_order',   'PO'),
    ('purchase_entry',   'GRN'),
    ('purchase_return',  'PRN'),
    ('sales_order',      'SO'),
    ('quotation',        'QT'),
    ('invoice',          'INV'),
    ('delivery',         'DEL'),
    ('credit_note',      'CN'),
    ('stock_transfer',   'STT'),
    ('stock_adjustment', 'ADJ'),
    ('production_lot',   'LOT'),
    ('material_issue',   'MIS'),
    ('production_entry', 'PE')
) v(doc_type, prefix)
ON CONFLICT (company_id, document_type) DO NOTHING;
