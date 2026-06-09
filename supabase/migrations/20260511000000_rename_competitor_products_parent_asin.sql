-- Prepare competitor_products for parent-ASIN grouped storage.
-- This migration is intentionally non-destructive for the old ASIN value:
-- product_asins preserves the product/listing ASINs grouped under parent_asin.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'competitor_products'
          AND column_name = 'our_asin'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'competitor_products'
          AND column_name = 'parent_asin'
    ) THEN
        ALTER TABLE public.competitor_products
            RENAME COLUMN our_asin TO parent_asin;
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'competitor_products'
          AND column_name = 'our_asin'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'competitor_products'
          AND column_name = 'parent_asin'
    ) THEN
        UPDATE public.competitor_products
        SET parent_asin = COALESCE(parent_asin, our_asin)
        WHERE parent_asin IS NULL;

    END IF;
END $$;

ALTER TABLE public.competitor_products
    ADD COLUMN IF NOT EXISTS product_asins TEXT[] NOT NULL DEFAULT '{}';

UPDATE public.competitor_products
SET product_asins = ARRAY[parent_asin]
WHERE product_asins = '{}'
  AND parent_asin IS NOT NULL;

ALTER TABLE public.competitor_products
    ALTER COLUMN parent_asin SET NOT NULL;

DROP INDEX IF EXISTS public.idx_competitor_products_lookup;

CREATE INDEX IF NOT EXISTS idx_competitor_products_parent_lookup
    ON public.competitor_products(parent_asin, marketplace);

CREATE INDEX IF NOT EXISTS idx_competitor_products_parent_category
    ON public.competitor_products(parent_asin, category_id, marketplace);
