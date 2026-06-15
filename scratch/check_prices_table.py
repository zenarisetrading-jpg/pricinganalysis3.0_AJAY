import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_db():
    url = os.getenv("PRICING_DATABASE_URL")
    if not url:
        print("PRICING_DATABASE_URL not set in environment.")
        return
    print(f"Connecting to database...")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    print("--- pb_price_events columns ---")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'pb_price_events';")
    for row in cur.fetchall():
        print(row)
        
    print("\n--- pb_price_snapshots_daily columns ---")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'pb_price_snapshots_daily';")
    for row in cur.fetchall():
        print(row)
        
    print("\n--- Testing our query with DISTINCT ON (asin) from pb_price_events ---")
    query = """
    WITH latest_prices AS (
        SELECT DISTINCT ON (asin, marketplace) 
            asin,
            marketplace,
            floor_price,
            buy_box_price,
            created_at
        FROM public.pb_price_events
        ORDER BY asin, marketplace, created_at DESC
    )
    SELECT 
        comp.asin AS competitor_asin,
        comp.brand,
        comp.title AS competitor_title,
        comp.last_bsr_rank AS bsr_rank,
        comp.source,
        comp.added_at AS pulled_at,
        comp.category_id,
        c.name AS category_name,
        lp.floor_price AS price_detail
    FROM public.pb_category_competitors comp
    JOIN public.pb_categories c ON comp.category_id = c.id
    LEFT JOIN latest_prices lp ON comp.asin = lp.asin AND comp.marketplace = lp.marketplace
    LIMIT 5;
    """
    try:
        cur.execute(query)
        print("Success! Results:")
        for r in cur.fetchall():
            print(r)
    except Exception as e:
        print(f"Failed: {e}")
        
    cur.close()
    conn.close()

if __name__ == '__main__':
    check_db()
