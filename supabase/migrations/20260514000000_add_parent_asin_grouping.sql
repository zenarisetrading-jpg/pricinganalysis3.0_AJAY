
-- Add parent_asin column to support parent-centric grouping in UI and analytics
ALTER TABLE public.pb_client_snapshots_daily ADD COLUMN IF NOT EXISTS parent_asin TEXT;
ALTER TABLE public.pb_recommendations ADD COLUMN IF NOT EXISTS parent_asin TEXT;
ALTER TABLE public.pb_alerts ADD COLUMN IF NOT EXISTS parent_asin TEXT;

-- Create indexes for faster grouping
CREATE INDEX IF NOT EXISTS idx_pb_client_snapshots_parent_asin ON public.pb_client_snapshots_daily(parent_asin);
CREATE INDEX IF NOT EXISTS idx_pb_recommendations_parent_asin ON public.pb_recommendations(parent_asin);
CREATE INDEX IF NOT EXISTS idx_pb_alerts_parent_asin ON public.pb_alerts(parent_asin);
