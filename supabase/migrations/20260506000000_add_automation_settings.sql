-- Add global settings table
CREATE TABLE IF NOT EXISTS public.pb_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed initial automation status
INSERT INTO public.pb_settings (key, value)
VALUES ('automation_enabled', 'true'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- Update event_type constraint to allow 'upload'
ALTER TABLE public.pb_price_events 
    DROP CONSTRAINT IF EXISTS pb_price_events_event_type_check;

ALTER TABLE public.pb_price_events 
    ADD CONSTRAINT pb_price_events_event_type_check 
    CHECK (event_type IN ('poll', 'any_offer_changed', 'upload'));

-- Grant access (assuming public schema usage matches existing patterns)
GRANT ALL ON public.pb_settings TO postgres;
GRANT ALL ON public.pb_settings TO anon;
GRANT ALL ON public.pb_settings TO authenticated;
GRANT ALL ON public.pb_settings TO service_role;
