
-- Add competitor_parent_asin to store the parent ASIN of competitors
ALTER TABLE public.competitor_products ADD COLUMN IF NOT EXISTS competitor_parent_asin TEXT;

-- Create index for faster parent-to-parent matching
CREATE INDEX IF NOT EXISTS idx_competitor_products_comp_parent ON public.competitor_products(competitor_parent_asin);
