-- =============================================================
-- APPAREL ERP — Full Database Schema
-- PostgreSQL 16
-- All migrations managed by Alembic; this file is the reference.
-- =============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fuzzy search

-- =============================================================
-- SYSTEM / INFRASTRUCTURE TABLES
-- =============================================================

CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    gstin           VARCHAR(15),
    pan             VARCHAR(10),
    address         TEXT,
    city            VARCHAR(100),
    state           VARCHAR(100),
    state_code      SMALLINT,
    pincode         VARCHAR(10),
    phone           VARCHAR(20),
    email           VARCHAR(200),
    website         VARCHAR(200),
    logo_url        TEXT,
    currency        VARCHAR(3) DEFAULT 'INR',
    default_hsn     VARCHAR(8),
    fabric_variance_pct  NUMERIC(5,2) DEFAULT 3.00,
    cost_of_capital_pct  NUMERIC(5,2),
    negative_stock_allowed BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    email           VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(200) NOT NULL,
    full_name       VARCHAR(200),
    phone           VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    is_owner        BOOLEAN NOT NULL DEFAULT false,
    last_login_at   TIMESTAMPTZ,
    failed_login_count SMALLINT DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    totp_secret     VARCHAR(64),
    totp_enabled    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, email)
);

CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, name)
);

CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(100) NOT NULL UNIQUE,  -- e.g. inventory.transfer
    description     VARCHAR(300)
);

CREATE TABLE role_permissions (
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(200) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    entity_type     VARCHAR(100) NOT NULL,
    entity_id       UUID NOT NULL,
    action          VARCHAR(50) NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    changed_fields  TEXT[],
    user_id         UUID REFERENCES users(id),
    ip_address      INET,
    request_id      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

CREATE TABLE document_sequences (
    company_id      UUID NOT NULL REFERENCES companies(id),
    document_type   VARCHAR(50) NOT NULL,
    prefix          VARCHAR(10) NOT NULL DEFAULT '',
    separator       VARCHAR(3) NOT NULL DEFAULT '/',
    year_format     VARCHAR(6) NOT NULL DEFAULT 'YY',
    next_number     INTEGER NOT NULL DEFAULT 1,
    padding         SMALLINT NOT NULL DEFAULT 4,
    PRIMARY KEY (company_id, document_type)
);

-- =============================================================
-- MASTER DATA
-- =============================================================

CREATE TABLE units (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(50) NOT NULL,
    abbreviation    VARCHAR(10) NOT NULL,
    unit_type       VARCHAR(20) NOT NULL,  -- weight, length, piece, volume
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, abbreviation)
);

CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(100) NOT NULL,
    UNIQUE (company_id, name)
);

CREATE TABLE sub_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    category_id     UUID NOT NULL REFERENCES categories(id),
    name            VARCHAR(100) NOT NULL
);

CREATE TABLE brands (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(100) NOT NULL,
    UNIQUE (company_id, name)
);

CREATE TABLE sizes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(20) NOT NULL,
    sort_order      SMALLINT DEFAULT 0,
    UNIQUE (company_id, name)
);

CREATE TABLE colours (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(100) NOT NULL,
    hex_code        VARCHAR(7),
    UNIQUE (company_id, name)
);

CREATE TABLE hsn_codes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hsn             VARCHAR(8) NOT NULL UNIQUE,
    description     VARCHAR(500),
    gst_rate        NUMERIC(5,2) NOT NULL DEFAULT 5.00,
    cess_rate       NUMERIC(5,2) DEFAULT 0.00
);

CREATE TABLE warehouses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(20),
    address         TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, code)
);

CREATE TABLE warehouse_locations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(20)
);

-- Products
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    code            VARCHAR(50) NOT NULL,
    name            VARCHAR(300) NOT NULL,
    category_id     UUID REFERENCES categories(id),
    sub_category_id UUID REFERENCES sub_categories(id),
    brand_id        UUID REFERENCES brands(id),
    product_type    VARCHAR(30) NOT NULL DEFAULT 'finished_good',
    -- finished_good | yarn | fabric | trim | packing | raw_material
    unit_id         UUID REFERENCES units(id),
    hsn_id          UUID REFERENCES hsn_codes(id),
    mrp             NUMERIC(15,2),
    dealer_price    NUMERIC(15,2),
    cost_price      NUMERIC(15,2),
    description     TEXT,
    -- Apparel-specific
    fabric_type     VARCHAR(100),
    fabric_composition TEXT,
    gsm             NUMERIC(8,2),
    construction    VARCHAR(100),
    fit             VARCHAR(50),
    season          VARCHAR(50),
    gender          VARCHAR(20),
    care_instructions TEXT,
    --
    is_active       BOOLEAN DEFAULT true,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, code)
);
CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_search ON products USING gin(to_tsvector('english', name || ' ' || code));

CREATE TABLE product_variants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id),
    sku             VARCHAR(100) NOT NULL,
    colour_id       UUID REFERENCES colours(id),
    size_id         UUID REFERENCES sizes(id),
    barcode         VARCHAR(50),
    mrp             NUMERIC(15,2),
    cost_price      NUMERIC(15,2),
    is_active       BOOLEAN DEFAULT true
);
-- NULL-safe unique constraint: treat NULL colour/size as a fixed sentinel UUID
-- so that (product, colour=NULL, size=S) and (product, colour=NULL, size=S) conflict correctly.
CREATE UNIQUE INDEX idx_product_variants_unique
    ON product_variants (
        product_id,
        COALESCE(colour_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(size_id,   '00000000-0000-0000-0000-000000000000'::uuid)
    );

CREATE TABLE product_images (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id),
    url             TEXT NOT NULL,
    is_primary      BOOLEAN DEFAULT false,
    sort_order      SMALLINT DEFAULT 0
);

-- Customers
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    code            VARCHAR(30) NOT NULL,
    legal_name      VARCHAR(300) NOT NULL,
    trade_name      VARCHAR(300),
    gstin           VARCHAR(15),
    pan             VARCHAR(10),
    customer_type   VARCHAR(30) DEFAULT 'domestic',
    -- domestic | export | sez
    credit_limit    NUMERIC(15,2) DEFAULT 0,
    credit_days     SMALLINT DEFAULT 30,
    price_list_id   UUID,
    sales_person_id UUID REFERENCES users(id),
    is_active       BOOLEAN DEFAULT true,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, code)
);
CREATE INDEX idx_customers_company ON customers(company_id);
CREATE INDEX idx_customers_search ON customers USING gin(to_tsvector('english', legal_name || ' ' || code));

CREATE TABLE customer_addresses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    address_type    VARCHAR(20) NOT NULL DEFAULT 'billing',
    -- billing | shipping
    line1           VARCHAR(300),
    line2           VARCHAR(300),
    city            VARCHAR(100),
    state           VARCHAR(100),
    state_code      SMALLINT,
    pincode         VARCHAR(10),
    country         VARCHAR(50) DEFAULT 'India',
    is_default      BOOLEAN DEFAULT false
);

CREATE TABLE customer_contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    name            VARCHAR(200) NOT NULL,
    designation     VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(200),
    is_primary      BOOLEAN DEFAULT false
);

-- Vendors
CREATE TABLE vendors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    code            VARCHAR(30) NOT NULL,
    name            VARCHAR(300) NOT NULL,
    gstin           VARCHAR(15),
    pan             VARCHAR(10),
    vendor_type     VARCHAR(30) DEFAULT 'supplier',
    -- supplier | job_worker | transporter
    payment_terms   SMALLINT DEFAULT 30,
    is_active       BOOLEAN DEFAULT true,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, code)
);

CREATE TABLE vendor_contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    name            VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(200),
    is_primary      BOOLEAN DEFAULT false
);

CREATE TABLE vendor_bank_details (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    bank_name       VARCHAR(200),
    account_number  VARCHAR(30),
    ifsc            VARCHAR(11),
    account_name    VARCHAR(200),
    is_primary      BOOLEAN DEFAULT false
);

-- Price Lists
CREATE TABLE price_lists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(200) NOT NULL,
    is_default      BOOLEAN DEFAULT false,
    valid_from      DATE,
    valid_to        DATE,
    UNIQUE (company_id, name)
);

CREATE TABLE price_list_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    price_list_id   UUID NOT NULL REFERENCES price_lists(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    min_quantity    NUMERIC(15,4) DEFAULT 0,
    max_quantity    NUMERIC(15,4),
    unit_price      NUMERIC(15,2) NOT NULL,
    discount_pct    NUMERIC(5,2) DEFAULT 0
);

-- =============================================================
-- INVENTORY
-- =============================================================

CREATE TABLE inventory_lots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    lot_number      VARCHAR(50) NOT NULL,
    material_type   VARCHAR(20) NOT NULL,
    -- yarn | fabric | trim | finished_good
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    -- Yarn-specific
    yarn_count      VARCHAR(20),
    ply             VARCHAR(10),
    mill            VARCHAR(200),
    fibre_type      VARCHAR(50),
    blend_composition TEXT,
    spinning_type   VARCHAR(30),
    treatment       VARCHAR(50),
    -- Fabric-specific
    construction    VARCHAR(100),
    gsm             NUMERIC(8,2),
    diameter_inches NUMERIC(8,2),
    colour          VARCHAR(100),
    finish          VARCHAR(100),
    -- Common
    supplier_id     UUID REFERENCES vendors(id),
    invoice_number  VARCHAR(100),
    invoice_date    DATE,
    unit_cost       NUMERIC(15,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, lot_number)
);

CREATE TABLE inventory_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    transaction_type VARCHAR(30) NOT NULL,
    reference_type  VARCHAR(50),
    reference_id    UUID,
    material_type   VARCHAR(20) NOT NULL,
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    location_id     UUID REFERENCES warehouse_locations(id),
    lot_id          UUID REFERENCES inventory_lots(id),
    quantity        NUMERIC(15,4) NOT NULL,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_cost       NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_cost      NUMERIC(15,2) NOT NULL DEFAULT 0,
    direction       SMALLINT NOT NULL CHECK (direction IN (1, -1)),
    transaction_date DATE NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID NOT NULL REFERENCES users(id)
);
CREATE INDEX idx_inv_tx_product ON inventory_transactions(product_id, warehouse_id);
CREATE INDEX idx_inv_tx_lot ON inventory_transactions(lot_id);
CREATE INDEX idx_inv_tx_reference ON inventory_transactions(reference_type, reference_id);
CREATE INDEX idx_inv_tx_date ON inventory_transactions(transaction_date DESC);

-- Materialised view for current balance (refreshed by Celery after each transaction)
CREATE MATERIALIZED VIEW inventory_balance AS
SELECT
    company_id,
    product_id,
    variant_id,
    warehouse_id,
    material_type,
    SUM(quantity * direction) AS current_qty,
    SUM(total_cost * direction) AS current_value
FROM inventory_transactions
GROUP BY company_id, product_id, variant_id, warehouse_id, material_type;

-- variant_id can be NULL; COALESCE to a fixed sentinel so two NULL-variant rows
-- for the same (company, product, warehouse, material_type) correctly conflict.
CREATE UNIQUE INDEX idx_inv_balance_pk
    ON inventory_balance(
        company_id,
        product_id,
        COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid),
        warehouse_id,
        material_type
    );

-- =============================================================
-- PURCHASE
-- =============================================================

CREATE TABLE purchase_orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    po_number       VARCHAR(50) NOT NULL,
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    order_date      DATE NOT NULL,
    expected_date   DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | approved | partial | received | cancelled
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT,
    terms           TEXT,
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, po_number)
);
CREATE INDEX idx_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX idx_po_status ON purchase_orders(status);

CREATE TABLE purchase_order_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    unit_id         UUID NOT NULL REFERENCES units(id),
    ordered_qty     NUMERIC(15,4) NOT NULL,
    received_qty    NUMERIC(15,4) NOT NULL DEFAULT 0,
    unit_price      NUMERIC(15,2) NOT NULL,
    discount_pct    NUMERIC(5,2) DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    gst_rate        NUMERIC(5,2) DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT
);

CREATE TABLE purchase_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    entry_number    VARCHAR(50) NOT NULL,
    purchase_order_id UUID REFERENCES purchase_orders(id),
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    entry_date      DATE NOT NULL,
    invoice_number  VARCHAR(100),
    invoice_date    DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, entry_number)
);

CREATE TABLE purchase_entry_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_entry_id UUID NOT NULL REFERENCES purchase_entries(id),
    po_item_id      UUID REFERENCES purchase_order_items(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    lot_id          UUID REFERENCES inventory_lots(id),
    unit_id         UUID NOT NULL REFERENCES units(id),
    received_qty    NUMERIC(15,4) NOT NULL,
    accepted_qty    NUMERIC(15,4) NOT NULL DEFAULT 0,
    rejected_qty    NUMERIC(15,4) NOT NULL DEFAULT 0,
    unit_price      NUMERIC(15,2) NOT NULL,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    quality_status  VARCHAR(20) DEFAULT 'pending',
    -- pending | accepted | rejected | partial
    notes           TEXT,
    -- FK to inventory_transactions created on acceptance
    inv_transaction_id UUID REFERENCES inventory_transactions(id)
);

-- =============================================================
-- CRM + SALES
-- =============================================================

CREATE TABLE leads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(300) NOT NULL,
    company_name    VARCHAR(300),
    email           VARCHAR(200),
    phone           VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'new',
    -- new | contacted | qualified | converted | lost
    source          VARCHAR(50),
    assigned_to     UUID REFERENCES users(id),
    converted_customer_id UUID REFERENCES customers(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id)
);

CREATE TABLE quotations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    quotation_number VARCHAR(50) NOT NULL,
    customer_id     UUID NOT NULL REFERENCES customers(id),
    contact_id      UUID REFERENCES customer_contacts(id),
    quotation_date  DATE NOT NULL,
    valid_until     DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | sent | approved | rejected | converted | cancelled
    billing_address_id UUID REFERENCES customer_addresses(id),
    price_list_id   UUID REFERENCES price_lists(id),
    subtotal        NUMERIC(15,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT,
    terms           TEXT,
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    converted_order_id UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, quotation_number)
);
CREATE INDEX idx_quotations_customer ON quotations(customer_id);
CREATE INDEX idx_quotations_status ON quotations(status);

CREATE TABLE quotation_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quotation_id    UUID NOT NULL REFERENCES quotations(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    description     VARCHAR(500),
    quantity        NUMERIC(15,4) NOT NULL,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_price      NUMERIC(15,2) NOT NULL,
    discount_pct    NUMERIC(5,2) DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL,
    gst_rate        NUMERIC(5,2) DEFAULT 0,
    cgst_rate       NUMERIC(5,2) DEFAULT 0,
    sgst_rate       NUMERIC(5,2) DEFAULT 0,
    igst_rate       NUMERIC(5,2) DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL,
    hsn_code        VARCHAR(8),
    sort_order      SMALLINT DEFAULT 0
);

CREATE TABLE sales_orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    order_number    VARCHAR(50) NOT NULL,
    quotation_id    UUID REFERENCES quotations(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    order_date      DATE NOT NULL,
    expected_delivery DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    -- confirmed | processing | partial | completed | cancelled
    subtotal        NUMERIC(15,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT,
    approved_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, order_number)
);

CREATE TABLE sales_order_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sales_order_id  UUID NOT NULL REFERENCES sales_orders(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    quantity        NUMERIC(15,4) NOT NULL,
    delivered_qty   NUMERIC(15,4) NOT NULL DEFAULT 0,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_price      NUMERIC(15,2) NOT NULL,
    discount_pct    NUMERIC(5,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL,
    gst_rate        NUMERIC(5,2) DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL,
    hsn_code        VARCHAR(8)
);

CREATE TABLE deliveries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    delivery_number VARCHAR(50) NOT NULL,
    sales_order_id  UUID NOT NULL REFERENCES sales_orders(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    delivery_date   DATE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | dispatched | delivered | cancelled
    transporter     VARCHAR(200),
    lr_number       VARCHAR(100),
    vehicle_number  VARCHAR(30),
    notes           TEXT,
    dispatched_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, delivery_number)
);

CREATE TABLE delivery_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    delivery_id     UUID NOT NULL REFERENCES deliveries(id),
    so_item_id      UUID NOT NULL REFERENCES sales_order_items(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    lot_id          UUID REFERENCES inventory_lots(id),
    quantity        NUMERIC(15,4) NOT NULL,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_price      NUMERIC(15,2) NOT NULL,
    total_amount    NUMERIC(15,2) NOT NULL,
    inv_transaction_id UUID REFERENCES inventory_transactions(id)
);

CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    invoice_number  VARCHAR(50) NOT NULL,
    sales_order_id  UUID REFERENCES sales_orders(id),
    delivery_id     UUID REFERENCES deliveries(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    invoice_date    DATE NOT NULL,
    due_date        DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'unpaid',
    -- unpaid | partial | paid | cancelled
    subtotal        NUMERIC(15,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(15,2) DEFAULT 0,
    taxable_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst_amount     NUMERIC(15,2) DEFAULT 0,
    sgst_amount     NUMERIC(15,2) DEFAULT 0,
    igst_amount     NUMERIC(15,2) DEFAULT 0,
    cess_amount     NUMERIC(15,2) DEFAULT 0,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
    paid_amount     NUMERIC(15,2) DEFAULT 0,
    balance_amount  NUMERIC(15,2) NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, invoice_number)
);

-- =============================================================
-- PRODUCTION
-- =============================================================

CREATE TABLE styles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(300) NOT NULL,
    code            VARCHAR(50),
    description     TEXT,
    garment_type    VARCHAR(50),
    gender          VARCHAR(20),
    season          VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE production_lots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    lot_number      VARCHAR(50) NOT NULL,
    style_id        UUID REFERENCES styles(id),
    customer_id     UUID REFERENCES customers(id),
    sales_order_id  UUID REFERENCES sales_orders(id),
    order_ref       VARCHAR(100),
    planned_qty     INTEGER NOT NULL DEFAULT 0,
    actual_qty      INTEGER NOT NULL DEFAULT 0,
    delivery_date   DATE,
    season          VARCHAR(50),
    target_sp       NUMERIC(15,2),
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    -- draft | planned | approved | material_pending | ready
    -- | in_production | qc | packing | ready_to_dispatch | completed | cancelled
    notes           TEXT,
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, lot_number)
);
CREATE INDEX idx_prod_lots_status ON production_lots(status);

CREATE TABLE production_lot_sizes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_lot_id UUID NOT NULL REFERENCES production_lots(id),
    size_id         UUID NOT NULL REFERENCES sizes(id),
    planned_qty     INTEGER NOT NULL DEFAULT 0,
    cut_qty         INTEGER NOT NULL DEFAULT 0,
    sewn_qty        INTEGER NOT NULL DEFAULT 0,
    finished_qty    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE production_stages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_lot_id UUID NOT NULL REFERENCES production_lots(id),
    stage_type      VARCHAR(30) NOT NULL,
    -- cutting | making | finishing | qc | packing | dispatch
    stage_name      VARCHAR(100) NOT NULL,
    planned_qty     INTEGER,
    input_qty       INTEGER DEFAULT 0,
    output_qty      INTEGER DEFAULT 0,
    rejected_qty    INTEGER DEFAULT 0,
    rework_qty      INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'pending',
    -- pending | in_progress | completed
    vendor_id       UUID REFERENCES vendors(id),  -- job worker
    rate_per_pc     NUMERIC(15,2),
    bill_amount     NUMERIC(15,2),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE production_stage_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stage_id        UUID NOT NULL REFERENCES production_stages(id),
    entry_date      DATE NOT NULL,
    pieces_in       INTEGER DEFAULT 0,
    pieces_out      INTEGER DEFAULT 0,
    rejected        INTEGER DEFAULT 0,
    operator        VARCHAR(200),
    machine         VARCHAR(100),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id)
);

CREATE TABLE fabric_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    run_number      VARCHAR(50) NOT NULL,
    construction    VARCHAR(200),
    input_lot_id    UUID REFERENCES inventory_lots(id),  -- input yarn/greige
    input_qty       NUMERIC(15,4),
    output_qty      NUMERIC(15,4),
    wastage_qty     NUMERIC(15,4),
    wastage_pct     NUMERIC(5,2),
    output_lot_id   UUID REFERENCES inventory_lots(id),  -- output fabric lot
    machine         VARCHAR(200),
    status          VARCHAR(20) DEFAULT 'open',
    -- open | closed
    started_at      DATE,
    closed_at       DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, run_number)
);

CREATE TABLE material_issues (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    issue_number    VARCHAR(50) NOT NULL,
    production_lot_id UUID NOT NULL REFERENCES production_lots(id),
    stage_id        UUID REFERENCES production_stages(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    issue_date      DATE NOT NULL,
    status          VARCHAR(20) DEFAULT 'issued',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, issue_number)
);

CREATE TABLE material_issue_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_issue_id UUID NOT NULL REFERENCES material_issues(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    variant_id      UUID REFERENCES product_variants(id),
    lot_id          UUID REFERENCES inventory_lots(id),
    planned_qty     NUMERIC(15,4),
    issued_qty      NUMERIC(15,4) NOT NULL,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_cost       NUMERIC(15,2) DEFAULT 0,
    total_cost      NUMERIC(15,2) DEFAULT 0,
    inv_transaction_id UUID REFERENCES inventory_transactions(id)
);

CREATE TABLE production_outputs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    output_number   VARCHAR(50) NOT NULL,
    production_lot_id UUID NOT NULL REFERENCES production_lots(id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(id),
    output_date     DATE NOT NULL,
    product_id      UUID NOT NULL REFERENCES products(id),
    quantity        NUMERIC(15,4) NOT NULL,
    unit_id         UUID NOT NULL REFERENCES units(id),
    unit_cost       NUMERIC(15,2) DEFAULT 0,
    total_cost      NUMERIC(15,2) DEFAULT 0,
    inv_transaction_id UUID REFERENCES inventory_transactions(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, output_number)
);

-- =============================================================
-- FINANCE
-- =============================================================

CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    payment_number  VARCHAR(50) NOT NULL,
    customer_id     UUID NOT NULL REFERENCES customers(id),
    payment_date    DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    payment_mode    VARCHAR(20) NOT NULL DEFAULT 'neft',
    reference       VARCHAR(100),
    bank_account    VARCHAR(100),
    notes           TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'recorded',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, payment_number)
);

CREATE TABLE payment_allocations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id          UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    invoice_id          UUID NOT NULL REFERENCES invoices(id),
    allocated_amount    NUMERIC(15,2) NOT NULL
);

CREATE TABLE vendor_payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    payment_number  VARCHAR(50) NOT NULL,
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    payment_date    DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    payment_mode    VARCHAR(20) NOT NULL DEFAULT 'neft',
    reference       VARCHAR(100),
    bank_account    VARCHAR(100),
    notes           TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'recorded',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, payment_number)
);

CREATE TABLE vendor_payment_allocations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_payment_id   UUID NOT NULL REFERENCES vendor_payments(id) ON DELETE CASCADE,
    purchase_entry_id   UUID NOT NULL REFERENCES purchase_entries(id),
    allocated_amount    NUMERIC(15,2) NOT NULL
);

CREATE TABLE credit_notes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id),
    credit_note_number  VARCHAR(50) NOT NULL,
    customer_id         UUID NOT NULL REFERENCES customers(id),
    invoice_id          UUID REFERENCES invoices(id),
    credit_note_date    DATE NOT NULL,
    reason              TEXT,
    taxable_amount      NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
    sgst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
    igst_amount         NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_amount        NUMERIC(15,2) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'issued',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          UUID REFERENCES users(id),
    UNIQUE (company_id, credit_note_number)
);

CREATE TABLE debit_notes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id),
    debit_note_number   VARCHAR(50) NOT NULL,
    vendor_id           UUID NOT NULL REFERENCES vendors(id),
    purchase_entry_id   UUID REFERENCES purchase_entries(id),
    debit_note_date     DATE NOT NULL,
    reason              TEXT,
    total_amount        NUMERIC(15,2) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'issued',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          UUID REFERENCES users(id),
    UNIQUE (company_id, debit_note_number)
);

CREATE TABLE expense_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    name            VARCHAR(100) NOT NULL,
    UNIQUE (company_id, name)
);

CREATE TABLE expenses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    expense_number  VARCHAR(50) NOT NULL,
    category_id     UUID REFERENCES expense_categories(id),
    vendor_id       UUID REFERENCES vendors(id),
    expense_date    DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    payment_method  VARCHAR(30),
    reference       VARCHAR(100),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID REFERENCES users(id),
    UNIQUE (company_id, expense_number)
);

-- =============================================================
-- FILE ATTACHMENTS (polymorphic)
-- =============================================================

CREATE TABLE file_attachments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    file_name       VARCHAR(300) NOT NULL,
    file_url        TEXT NOT NULL,
    file_size       INTEGER,
    mime_type       VARCHAR(100),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by     UUID REFERENCES users(id)
);
CREATE INDEX idx_attachments_entity ON file_attachments(entity_type, entity_id);

-- =============================================================
-- NOTIFICATIONS
-- =============================================================

CREATE TABLE notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID NOT NULL REFERENCES companies(id),
    user_id             UUID REFERENCES users(id),
    notification_type   VARCHAR(50) NOT NULL,
    title               VARCHAR(200) NOT NULL,
    body                TEXT NOT NULL,
    data                JSONB,
    is_read             BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);

-- =============================================================
-- AI AGENT CONVERSATIONS
-- =============================================================

CREATE TABLE agent_conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(300),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);

CREATE TABLE agent_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES agent_conversations(id),
    role            VARCHAR(10) NOT NULL,  -- user | assistant | tool
    content         TEXT NOT NULL,
    tool_calls      JSONB,
    tool_results    JSONB,
    tokens_used     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_agent_msgs_conv ON agent_messages(conversation_id, created_at);

-- =============================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================

-- Common filter patterns
CREATE INDEX idx_po_company_status ON purchase_orders(company_id, status);
CREATE INDEX idx_so_company_status ON sales_orders(company_id, status);
CREATE INDEX idx_invoices_customer_status ON invoices(customer_id, status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date) WHERE status != 'paid';
CREATE INDEX idx_prod_lots_company ON production_lots(company_id, status);
CREATE INDEX idx_users_company ON users(company_id);

-- Full-text search
CREATE INDEX idx_vendors_search ON vendors USING gin(to_tsvector('english', name || ' ' || code));
