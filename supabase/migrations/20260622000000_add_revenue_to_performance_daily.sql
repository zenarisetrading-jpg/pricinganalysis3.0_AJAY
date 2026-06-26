ALTER TABLE public.pb_client_performance_daily
    ADD COLUMN IF NOT EXISTS revenue NUMERIC(12, 2);
