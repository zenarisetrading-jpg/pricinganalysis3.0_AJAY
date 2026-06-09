-- PRICE BENCHMARKING MODULE
-- Standalone schema derived from PRD v2.

CREATE TABLE IF NOT EXISTS public.pb_organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'seller' CHECK (type IN ('seller', 'agency')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.pb_clients (
    client_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES public.pb_organizations(org_id),
    name TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    sp_api_profile_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (org_id, marketplace)
);

CREATE TABLE IF NOT EXISTS public.pb_categories (
    id BIGSERIAL PRIMARY KEY,
    keepa_cat_id BIGINT NOT NULL,
    marketplace TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (keepa_cat_id, marketplace)
);

CREATE TABLE IF NOT EXISTS public.pb_category_competitors (
    id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES public.pb_categories(id) ON DELETE CASCADE,
    marketplace TEXT NOT NULL,
    asin TEXT NOT NULL,
    title TEXT,
    brand TEXT,
    source TEXT NOT NULL DEFAULT 'keepa_bsr',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_bsr_rank INT,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (category_id, asin)
);

CREATE INDEX IF NOT EXISTS idx_cat_competitors_lookup
    ON public.pb_category_competitors(category_id, marketplace, is_active);

CREATE TABLE IF NOT EXISTS public.pb_client_competitor_overrides (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('exclude', 'include')),
    manually_set BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT,
    set_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, asin)
);

CREATE TABLE IF NOT EXISTS public.pb_benchmarking_skus (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    category_id BIGINT REFERENCES public.pb_categories(id),
    product_title TEXT,
    strategy TEXT NOT NULL DEFAULT 'mid'
        CHECK (strategy IN ('value', 'mid', 'premium', 'floor', 'custom')),
    min_price NUMERIC(10, 2),
    max_price NUMERIC(10, 2),
    fallback_price NUMERIC(10, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, asin)
);

CREATE INDEX IF NOT EXISTS idx_pb_skus_client
    ON public.pb_benchmarking_skus(client_id, is_active);

CREATE TABLE IF NOT EXISTS public.pb_price_events (
    id BIGSERIAL PRIMARY KEY,
    asin TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'poll'
        CHECK (event_type IN ('poll', 'any_offer_changed')),
    floor_price NUMERIC(10, 2),
    ceiling_price NUMERIC(10, 2),
    median_price NUMERIC(10, 2),
    mean_price NUMERIC(10, 2),
    n_offers INT,
    buy_box_price NUMERIC(10, 2),
    buy_box_is_fba BOOLEAN,
    foep NUMERIC(10, 2),
    competitive_price NUMERIC(10, 2),
    offers_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pb_events_asin_time
    ON public.pb_price_events(asin, marketplace, created_at DESC);

CREATE TABLE IF NOT EXISTS public.pb_price_snapshots_daily (
    id BIGSERIAL PRIMARY KEY,
    asin TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    n_events INT,
    floor_price NUMERIC(10, 2),
    ceiling_price NUMERIC(10, 2),
    median_price NUMERIC(10, 2),
    mean_price NUMERIC(10, 2),
    p25_price NUMERIC(10, 2),
    p75_price NUMERIC(10, 2),
    buy_box_price NUMERIC(10, 2),
    foep NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asin, marketplace, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_pb_daily_asin_date
    ON public.pb_price_snapshots_daily(asin, marketplace, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS public.pb_client_snapshots_daily (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id),
    sku_id TEXT NOT NULL,
    asin TEXT NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    your_price NUMERIC(10, 2),
    n_competitors INT,
    floor_price NUMERIC(10, 2),
    ceiling_price NUMERIC(10, 2),
    median_price NUMERIC(10, 2),
    p25_price NUMERIC(10, 2),
    p75_price NUMERIC(10, 2),
    percentile_rank NUMERIC(5, 2),
    index_vs_median NUMERIC(6, 1),
    zone TEXT,
    strategy TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, asin, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_pb_client_snapshots_lookup
    ON public.pb_client_snapshots_daily(client_id, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS public.pb_alerts (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id),
    asin TEXT NOT NULL,
    sku_id TEXT,
    marketplace TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    action_hint TEXT,
    metadata JSONB,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pb_alerts_client
    ON public.pb_alerts(client_id, is_resolved, severity, created_at DESC);

CREATE TABLE IF NOT EXISTS public.pb_recommendations (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.pb_clients(client_id),
    asin TEXT NOT NULL,
    sku_id TEXT,
    marketplace TEXT NOT NULL,
    strategy TEXT NOT NULL,
    current_price NUMERIC(10, 2),
    recommended_price NUMERIC(10, 2),
    change_amount NUMERIC(10, 2),
    change_pct NUMERIC(6, 2),
    action TEXT NOT NULL CHECK (action IN ('increase', 'decrease', 'hold')),
    confidence TEXT NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    reasoning TEXT,
    metadata JSONB,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'applied', 'dismissed')),
    applied_at TIMESTAMPTZ,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pb_recs_client
    ON public.pb_recommendations(client_id, status, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS public.pb_runs (
    id BIGSERIAL PRIMARY KEY,
    run_type TEXT NOT NULL CHECK (run_type IN ('snapshot', 'aggregation', 'discovery', 'event')),
    client_id TEXT REFERENCES public.pb_clients(client_id),
    marketplace TEXT,
    run_date DATE NOT NULL DEFAULT CURRENT_DATE,
    n_asins INT,
    n_events INT,
    n_alerts INT,
    n_recommendations INT,
    status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'partial', 'failed')),
    error_log TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION public.update_pb_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pb_skus_updated_at ON public.pb_benchmarking_skus;
CREATE TRIGGER trg_pb_skus_updated_at
    BEFORE UPDATE ON public.pb_benchmarking_skus
    FOR EACH ROW EXECUTE FUNCTION public.update_pb_updated_at();

DROP TRIGGER IF EXISTS trg_pb_cat_competitors_updated_at ON public.pb_category_competitors;
CREATE TRIGGER trg_pb_cat_competitors_updated_at
    BEFORE UPDATE ON public.pb_category_competitors
    FOR EACH ROW EXECUTE FUNCTION public.update_pb_updated_at();
