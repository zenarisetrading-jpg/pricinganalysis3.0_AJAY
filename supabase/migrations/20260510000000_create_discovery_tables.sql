-- Migration to create competitor discovery and analysis tables

-- Table for raw competitor products discovered via scraping
CREATE TABLE IF NOT EXISTS public.competitor_products (
    id BIGSERIAL PRIMARY KEY,
    our_asin TEXT NOT NULL,
    competitor_asin TEXT NOT NULL,
    category_id TEXT,
    competitor_title TEXT,
    competitor_price NUMERIC(10, 2),
    rating NUMERIC(3, 2),
    reviews INT,
    rank INT,
    brand TEXT,
    product_url TEXT,
    marketplace TEXT NOT NULL DEFAULT 'UAE',
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_competitor_products_lookup 
    ON public.competitor_products(our_asin, marketplace);
CREATE INDEX IF NOT EXISTS idx_competitor_products_cat 
    ON public.competitor_products(category_id);

-- Table for stored pricing analysis summaries
CREATE TABLE IF NOT EXISTS public.pricing_analysis (
    id BIGSERIAL PRIMARY KEY,
    asin TEXT NOT NULL,
    marketplace TEXT NOT NULL DEFAULT 'UAE',
    lowest_price NUMERIC(10, 2),
    highest_price NUMERIC(10, 2),
    average_price NUMERIC(10, 2),
    median_price NUMERIC(10, 2),
    recommended_price NUMERIC(10, 2),
    premium_price NUMERIC(10, 2),
    value_price NUMERIC(10, 2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asin, marketplace)
);

CREATE INDEX IF NOT EXISTS idx_pricing_analysis_lookup 
    ON public.pricing_analysis(asin, marketplace);
