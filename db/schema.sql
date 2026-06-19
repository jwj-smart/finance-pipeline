-- ==========================================
-- 1. DIMENSION TABLES
-- ==========================================

CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,                       -- e.g., 20260619
    calendar_date DATE NOT NULL UNIQUE,            -- e.g., '2026-06-19'
    year INT NOT NULL,
    quarter INT NOT NULL,
    month_number INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_uk_business_day BOOLEAN NOT NULL DEFAULT TRUE  -- Crucial for filtering market holidays
);

CREATE TABLE dim_assets (
    asset_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- Auto-incrementing internal ID
    ticker VARCHAR(12) NOT NULL UNIQUE,                    -- e.g., 'SONIA', 'GB10Y=F'
    asset_name VARCHAR(100) NOT NULL,                      -- e.g., 'Sterling Overnight Index Average'
    asset_class VARCHAR(30) NOT NULL,                      -- e.g., 'Benchmark', 'Fixed Income', 'Equity'
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',            -- e.g., 'GBP', 'USD'
    is_benchmark BOOLEAN NOT NULL DEFAULT FALSE            -- Flags core focus metrics
);

CREATE TABLE dim_macro_indicators (
    indicator_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indicator_code VARCHAR(30) NOT NULL UNIQUE,            -- e.g., 'UK_CPI_YOY'
    indicator_name VARCHAR(100) NOT NULL,                  -- e.g., 'UK Consumer Price Index YoY'
    frequency VARCHAR(20) NOT NULL                         -- e.g., 'Monthly', 'Quarterly'
);

-- ==========================================
-- 2. FACT TABLES (With Foreign Keys & Check Constraints)
-- ==========================================

CREATE TABLE fact_market_prices (
    price_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_id INT NOT NULL,
    asset_id INT NOT NULL,
    open_price NUMERIC(12, 4),
    high_price NUMERIC(12, 4),
    low_price NUMERIC(12, 4),
    close_price NUMERIC(12, 4) NOT NULL,
    volume BIGINT,
    
    -- Constraints linking back to our dimensions
    CONSTRAINT fk_market_date FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    CONSTRAINT fk_market_asset FOREIGN KEY (asset_id) REFERENCES dim_assets(asset_id),
    
    -- Composite Unique Constraint: Prevents duplicate rows for the same asset on the same day
    CONSTRAINT uq_asset_date UNIQUE (date_id, asset_id),
    
    -- Integrity Check: Prices can't be negative
    CONSTRAINT chk_positive_close CHECK (close_price >= 0)
);

CREATE TABLE fact_macro_data (
    macro_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_id INT NOT NULL,
    indicator_id INT NOT NULL,
    value NUMERIC(8, 4) NOT NULL,                          -- e.g., 2.5000 for 2.5% inflation
    
    CONSTRAINT fk_macro_date FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    CONSTRAINT fk_macro_indicator FOREIGN KEY (indicator_id) REFERENCES dim_macro_indicators(indicator_id),
    CONSTRAINT uq_indicator_date UNIQUE (date_id, indicator_id)
);

-- Enable RLS on all tables to silence the warning and secure the public API
ALTER TABLE dim_date ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_macro_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_market_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_macro_data ENABLE ROW LEVEL SECURITY;