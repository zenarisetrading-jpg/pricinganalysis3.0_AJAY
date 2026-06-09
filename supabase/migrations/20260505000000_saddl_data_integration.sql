-- SADDL DATA INTEGRATION SCHEMA
-- Migration for account and BSR data orchestration as per SADDL_Data_Migration_Spec.md

-- Create sc_raw schema if not exists
CREATE SCHEMA IF NOT EXISTS sc_raw;

-- Create sc_analytics schema if not exists
CREATE SCHEMA IF NOT EXISTS sc_analytics;

-- 1. Account Management (Public Schema)
CREATE TABLE IF NOT EXISTS public.accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    organization_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. BSR & Category Tracking (sc_raw Schema)
CREATE TABLE IF NOT EXISTS sc_raw.bsr_history (
    id BIGSERIAL PRIMARY KEY,
    asin TEXT NOT NULL,
    marketplace_id TEXT NOT NULL, -- This links to accounts.account_id
    category_name TEXT NOT NULL,
    rank INTEGER NOT NULL,
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_date, marketplace_id, asin, category_name)
);

-- 3. BSR Trends View (sc_analytics Schema)
CREATE OR REPLACE VIEW sc_analytics.bsr_trends AS
WITH current_ranks AS (
    SELECT 
        asin, 
        category_name, 
        rank as current_rank,
        report_date
    FROM sc_raw.bsr_history
    WHERE report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
),
prev_ranks AS (
    SELECT 
        asin, 
        category_name, 
        rank as rank_7d_ago
    FROM sc_raw.bsr_history
    WHERE report_date = (SELECT MAX(report_date) - INTERVAL '7 days' FROM sc_raw.bsr_history)
)
SELECT 
    c.asin, 
    c.category_name, 
    c.current_rank, 
    COALESCE(p.rank_7d_ago, c.current_rank) as rank_7d_ago,
    CASE 
        WHEN p.rank_7d_ago IS NULL THEN 'NEW'
        WHEN c.current_rank < p.rank_7d_ago THEN 'IMPROVING'
        WHEN c.current_rank > p.rank_7d_ago THEN 'DECLINING'
        ELSE 'STABLE'
    END as rank_status_7d
FROM current_ranks c
LEFT JOIN prev_ranks p ON c.asin = p.asin AND c.category_name = p.category_name;
