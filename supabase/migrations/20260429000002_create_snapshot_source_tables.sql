-- Standalone source tables required by PRD section 0 lookup.
-- These provide the concrete equivalents of the existing SADDL integrations:
-- - SP-API profiles table
-- - listings/pricing table
-- - performance table

CREATE TABLE IF NOT EXISTS public.pb_sp_api_profiles (
    profile_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id) ON DELETE CASCADE,
    marketplace TEXT NOT NULL,
    seller_id TEXT,
    refresh_token_ref TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, marketplace)
);

CREATE INDEX IF NOT EXISTS idx_pb_sp_api_profiles_client
    ON public.pb_sp_api_profiles(client_id, marketplace, is_active);

CREATE TABLE IF NOT EXISTS public.pb_client_listings (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id) ON DELETE CASCADE,
    marketplace TEXT NOT NULL,
    asin TEXT NOT NULL,
    sku_id TEXT,
    listing_price NUMERIC(10, 2),
    price NUMERIC(10, 2),
    currency TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, asin, marketplace)
);

CREATE INDEX IF NOT EXISTS idx_pb_client_listings_lookup
    ON public.pb_client_listings(client_id, marketplace, asin);

CREATE TABLE IF NOT EXISTS public.pb_client_performance_daily (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id) ON DELETE CASCADE,
    marketplace TEXT NOT NULL,
    asin TEXT NOT NULL,
    performance_date DATE NOT NULL DEFAULT CURRENT_DATE,
    units_ordered INT,
    sessions INT,
    acos NUMERIC(6, 2),
    cvr NUMERIC(6, 2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, asin, marketplace, performance_date)
);

CREATE INDEX IF NOT EXISTS idx_pb_client_perf_lookup
    ON public.pb_client_performance_daily(client_id, marketplace, asin, performance_date DESC);
