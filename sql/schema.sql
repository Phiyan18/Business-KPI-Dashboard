-- Business KPI Data Warehouse Schema
-- PostgreSQL Version

-- Drop existing tables
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_customers CASCADE;
DROP TABLE IF EXISTS dim_products CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS fact_kpis CASCADE;
DROP TABLE IF EXISTS fact_data_quality CASCADE;
DROP TABLE IF EXISTS log_data_errors CASCADE;

-- Dimension: Date
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER
);

-- Dimension: Customers
CREATE TABLE dim_customers (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(200),
    email VARCHAR(200),
    segment VARCHAR(50),
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    registration_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Products
CREATE TABLE dim_products (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    sub_category VARCHAR(100),
    unit_cost DECIMAL(10,2),
    unit_price DECIMAL(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Sales Transactions
CREATE TABLE fact_sales (
    sale_key SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    date_key INTEGER REFERENCES dim_date(date_key),
    customer_key INTEGER REFERENCES dim_customers(customer_key),
    product_key INTEGER REFERENCES dim_products(product_key),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    discount DECIMAL(5,2),
    shipping_cost DECIMAL(10,2),
    revenue DECIMAL(12,2),
    cost DECIMAL(12,2),
    profit DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: KPI Metrics
CREATE TABLE fact_kpis (
    kpi_key SERIAL PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    kpi_name VARCHAR(100) NOT NULL,
    kpi_value DECIMAL(15,4),
    target_value DECIMAL(15,4),
    variance DECIMAL(15,4),
    variance_pct DECIMAL(8,2),
    status VARCHAR(20), -- 'Good', 'Warning', 'Critical'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Data Quality Metrics
CREATE TABLE fact_data_quality (
    dq_key SERIAL PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    table_name VARCHAR(100),
    total_records INTEGER,
    complete_records INTEGER,
    completeness_pct DECIMAL(5,2),
    duplicate_records INTEGER,
    duplicate_pct DECIMAL(5,2),
    null_count INTEGER,
    outlier_count INTEGER,
    error_count INTEGER,
    quality_score DECIMAL(5,2),
    status VARCHAR(20), -- 'Pass', 'Warning', 'Fail'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log: Data Errors
CREATE TABLE log_data_errors (
    error_key SERIAL PRIMARY KEY,
    error_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name VARCHAR(100),
    column_name VARCHAR(100),
    error_type VARCHAR(50), -- 'Missing', 'Duplicate', 'Outlier', 'Invalid'
    error_description TEXT,
    record_id VARCHAR(100),
    severity VARCHAR(20) -- 'Low', 'Medium', 'High', 'Critical'
);

-- Create indexes for better performance
CREATE INDEX idx_sales_date ON fact_sales(date_key);
CREATE INDEX idx_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_sales_product ON fact_sales(product_key);
CREATE INDEX idx_kpis_date ON fact_kpis(date_key);
CREATE INDEX idx_kpis_name ON fact_kpis(kpi_name);
CREATE INDEX idx_dq_date ON fact_data_quality(date_key);
CREATE INDEX idx_dq_table ON fact_data_quality(table_name);
CREATE INDEX idx_errors_timestamp ON log_data_errors(error_timestamp);
CREATE INDEX idx_errors_table ON log_data_errors(table_name);

-- Create views for Power BI
CREATE OR REPLACE VIEW vw_sales_summary AS
SELECT 
    d.full_date,
    d.year,
    d.month_name,
    c.customer_name,
    c.segment,
    c.country,
    p.product_name,
    p.category,
    p.sub_category,
    s.quantity,
    s.revenue,
    s.cost,
    s.profit,
    s.discount
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
JOIN dim_customers c ON s.customer_key = c.customer_key
JOIN dim_products p ON s.product_key = p.product_key;

CREATE OR REPLACE VIEW vw_kpi_dashboard AS
SELECT 
    d.full_date,
    d.year,
    d.month_name,
    k.kpi_name,
    k.kpi_value,
    k.target_value,
    k.variance,
    k.variance_pct,
    k.status
FROM fact_kpis k
JOIN dim_date d ON k.date_key = d.date_key
ORDER BY d.full_date DESC, k.kpi_name;

CREATE OR REPLACE VIEW vw_data_quality_dashboard AS
SELECT 
    d.full_date,
    dq.table_name,
    dq.total_records,
    dq.completeness_pct,
    dq.duplicate_pct,
    dq.error_count,
    dq.quality_score,
    dq.status
FROM fact_data_quality dq
JOIN dim_date d ON dq.date_key = d.date_key
ORDER BY d.full_date DESC, dq.table_name;

CREATE OR REPLACE VIEW vw_error_log AS
SELECT 
    error_timestamp,
    table_name,
    column_name,
    error_type,
    error_description,
    severity,
    COUNT(*) OVER (PARTITION BY table_name, error_type) as error_frequency
FROM log_data_errors
ORDER BY error_timestamp DESC;