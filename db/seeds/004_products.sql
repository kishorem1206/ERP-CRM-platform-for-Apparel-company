-- =============================================================
-- Phase 0: Product Master — Real inventory items
-- Yarns | Fabric | Trims | Packing Materials | Styles
-- =============================================================

-- ─── YARNS ────────────────────────────────────────────────────
-- product_type = 'yarn', unit = kg, HSN = 5509
INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    c.id,
    v.code,
    v.name,
    'yarn',
    (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'kg'),
    (SELECT id FROM hsn_codes WHERE hsn = '5509'),
    (SELECT id FROM categories WHERE company_id = c.id AND name = 'Yarn'),
    true,
    NOW(), NOW()
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('YARN-30S-VL', '30s VL - Viscose Lycra Yarn 30 Count'),
    ('YARN-30S-RL', '30s RL - Ring Lycra Yarn 30 Count'),
    ('YARN-40S-VL', '40s VL - Viscose Lycra Yarn 40 Count'),
    ('YARN-40S-RL', '40s RL - Ring Lycra Yarn 40 Count')
) v(code, name)
ON CONFLICT (company_id, code) DO NOTHING;

-- ─── FABRIC ───────────────────────────────────────────────────
-- Notation: Count-KnitType-Colour-Diameter
-- product_type = 'fabric', unit = kg, HSN = 6006
INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, sub_category_id,
                      fabric_type, fabric_composition, gsm, construction, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    c.id,
    v.code,
    v.name,
    'fabric',
    (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'kg'),
    (SELECT id FROM hsn_codes WHERE hsn = '6006'),
    (SELECT id FROM categories WHERE company_id = c.id AND name = 'Fabric'),
    (SELECT id FROM sub_categories sc
        JOIN categories cat ON sc.category_id = cat.id
        WHERE cat.company_id = c.id AND cat.name = 'Fabric' AND sc.name = 'Single Jersey'),
    v.fabric_type,
    v.composition,
    v.gsm,
    v.construction,
    true,
    NOW(), NOW()
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('FAB-30VL-SJ-PNK-30', '30sVL S/J Pink 30" Dia',  'Single Jersey', '30s Viscose Lycra', 160.00, 'S/J - 30" dia'),
    ('FAB-40RL-SJ-WHT-16', '40sRL S/J White 16" Dia',  'Single Jersey', '40s Ring Lycra',    180.00, 'S/J - 16" dia')
) v(code, name, fabric_type, composition, gsm, construction)
ON CONFLICT (company_id, code) DO NOTHING;

-- ─── TRIMS ────────────────────────────────────────────────────
-- Buttons: unit = grs (gross = 144 pcs), HSN = 9606
-- Elastic: unit = m (metre), HSN = 5806
INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, sub_category_id, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    c.id,
    v.code,
    v.name,
    'trim',
    CASE v.unit_abbr
        WHEN 'grs' THEN (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'grs')
        ELSE (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'm')
    END,
    (SELECT id FROM hsn_codes WHERE hsn = v.hsn),
    (SELECT id FROM categories WHERE company_id = c.id AND name = 'Trim'),
    (SELECT id FROM sub_categories sc
        JOIN categories cat ON sc.category_id = cat.id
        WHERE cat.company_id = c.id AND cat.name = 'Trim' AND sc.name = v.sub_cat),
    true,
    NOW(), NOW()
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('TRIM-BTN-12MM-WHT', 'Button 12mm White',       'grs', '9606', 'Buttons'),
    ('TRIM-BTN-10MM-BRN', 'Button 10mm Brown',       'grs', '9606', 'Buttons'),
    ('TRIM-ELS-35MM-LYC', 'Elastic 35mm Lycra',      'm',   '5806', 'Elastic'),
    ('TRIM-ELS-20MM-3WF', 'Elastic 20mm 3 Weft',     'm',   '5806', 'Elastic')
) v(code, name, unit_abbr, hsn, sub_cat)
ON CONFLICT (company_id, code) DO NOTHING;

-- ─── PACKING MATERIALS ────────────────────────────────────────
-- All unit = pcs
INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, sub_category_id, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    c.id,
    v.code,
    v.name,
    'packing',
    (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'pcs'),
    (SELECT id FROM hsn_codes WHERE hsn = v.hsn),
    (SELECT id FROM categories WHERE company_id = c.id AND name = 'Packing Material'),
    (SELECT id FROM sub_categories sc
        JOIN categories cat ON sc.category_id = cat.id
        WHERE cat.company_id = c.id AND cat.name = 'Packing Material' AND sc.name = v.sub_cat),
    true,
    NOW(), NOW()
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('PACK-ICARD-7.5X11',  'Inner Card 7.5"x11"',               '4823', 'Inner Card'),
    ('PACK-BOPP-8.5X11P2', 'BOPP Bag 8.5"x11"+2"',              '3923', 'Poly Bag'),
    ('PACK-GASET-5X9.25',  'Gusset Bag 5*9.25*2.75 flap+1.75"', '3923', 'Poly Bag'),
    ('PACK-CTN-24X18X14',  'Carton 24"x18"x14"',                '4819', 'Carton')
) v(code, name, hsn, sub_cat)
ON CONFLICT (company_id, code) DO NOTHING;

-- ─── FINISHED GOODS / STYLES ──────────────────────────────────
-- SK prefix styles: knitted garments HSN 6109
-- IC prefix styles: infant garments HSN 6111
-- Unit = pcs (sold by piece); also tracked in dzn (dozen)
INSERT INTO products (id, company_id, code, name, product_type, unit_id, hsn_id, category_id, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    c.id,
    v.code,
    v.name,
    'finished_good',
    (SELECT id FROM units WHERE company_id = c.id AND abbreviation = 'pcs'),
    (SELECT id FROM hsn_codes WHERE hsn = v.hsn),
    (SELECT id FROM categories WHERE company_id = c.id AND name = 'Finished Goods'),
    true,
    NOW(), NOW()
FROM (SELECT id FROM companies LIMIT 1) c
CROSS JOIN (VALUES
    ('SK-203-50', 'Style SK-203-50', '6109'),
    ('SK-245-50', 'Style SK-245-50', '6109'),
    ('IC-2',      'Style IC-2',      '6111'),
    ('IC-338',    'Style IC-338',    '6111')
) v(code, name, hsn)
ON CONFLICT (company_id, code) DO NOTHING;

-- ─── STYLE VARIANTS: SK styles (adult sizes S, M, L, XL, XXL) ─
-- ON CONFLICT DO NOTHING works with the expression unique index on product_variants
INSERT INTO product_variants (id, product_id, sku, size_id, is_active)
SELECT
    gen_random_uuid(),
    p.id,
    p.code || '-' || sz.name,
    sz.id,
    true
FROM products p
JOIN (SELECT id FROM companies LIMIT 1) c ON p.company_id = c.id
JOIN sizes sz ON sz.company_id = c.id AND sz.name IN ('S', 'M', 'L', 'XL', 'XXL')
WHERE p.code IN ('SK-203-50', 'SK-245-50')
ON CONFLICT DO NOTHING;

-- ─── STYLE VARIANTS: IC styles (infant sizes 3M–24M) ──────────
INSERT INTO product_variants (id, product_id, sku, size_id, is_active)
SELECT
    gen_random_uuid(),
    p.id,
    p.code || '-' || sz.name,
    sz.id,
    true
FROM products p
JOIN (SELECT id FROM companies LIMIT 1) c ON p.company_id = c.id
JOIN sizes sz ON sz.company_id = c.id AND sz.name IN ('3M', '6M', '9M', '12M', '18M', '24M')
WHERE p.code IN ('IC-2', 'IC-338')
ON CONFLICT DO NOTHING;
