-- =============================================================================
-- PRICE BENCHMARKING MODULE — SCHEMA MIGRATION v2 → v3
-- Run this in Supabase SQL Editor to add Apify-specific fields
-- =============================================================================

-- Add Apify-specific fields to Tier 1 events table
ALTER TABLE pb_price_events 
    ADD COLUMN IF NOT EXISTS seller_name TEXT,
    ADD COLUMN IF NOT EXISTS is_buy_box_winner BOOLEAN,
    ADD COLUMN IF NOT EXISTS shipping_price NUMERIC(10,2);

-- Update categories table to remove Keepa dependency
ALTER TABLE pb_categories 
    ADD COLUMN IF NOT EXISTS apify_search_query TEXT,
    ADD COLUMN IF NOT EXISTS apify_category_url TEXT;

-- Add index for faster webhook lookups
CREATE INDEX IF NOT EXISTS idx_price_events_asin_marketplace 
    ON pb_price_events(asin, marketplace, created_at DESC);

-- Update competitor source field to allow 'apify'
ALTER TABLE pb_category_competitors 
    DROP CONSTRAINT IF EXISTS pb_category_competitors_source_check;

ALTER TABLE pb_category_competitors 
    ADD CONSTRAINT pb_category_competitors_source_check 
    CHECK (source IN ('keepa_bsr', 'apify_bsr', 'apify_search', 'manual_admin'));
