import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_discovery_tables():
    # You need to provide your Supabase DB connection string here.
    # It usually looks like: postgresql://postgres.[project-id]:[password]@[host]:5432/postgres
    # You can find it in Supabase Settings -> Database -> Connection string
    
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("SADDL_DATABASE_URL")
    
    if not db_url:
        print("Error: No database URL found.")
        print("Please set SUPABASE_DB_URL in your .env file.")
        return

    print(f"Connecting to database...")
    
    sql = """
    -- Table for raw competitor products discovered via scraping
    CREATE TABLE IF NOT EXISTS public.competitor_products (
        id BIGSERIAL PRIMARY KEY,
        parent_asin TEXT NOT NULL,
        product_asins TEXT[] NOT NULL DEFAULT '{}',
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

    CREATE UNIQUE INDEX IF NOT EXISTS uq_competitor_products_parent_competitor
        ON public.competitor_products(parent_asin, category_id, competitor_asin, marketplace);
    CREATE INDEX IF NOT EXISTS idx_competitor_products_lookup 
        ON public.competitor_products(parent_asin, marketplace);
    CREATE INDEX IF NOT EXISTS idx_competitor_products_parent_category 
        ON public.competitor_products(parent_asin, category_id, marketplace);
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
    """

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Executing table creation SQL...")
        cur.execute(sql)
        
        print("✅ Success! Tables created/verified in the database.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    create_discovery_tables()
