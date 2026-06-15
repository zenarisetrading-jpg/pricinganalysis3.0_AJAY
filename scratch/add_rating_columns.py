import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("PRICING_DATABASE_URL")
if not db_url:
    print("[ERROR] PRICING_DATABASE_URL not found in environment variables.")
    exit(1)

try:
    print("Connecting to database to verify columns...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # 1. Add columns to pb_price_events
    print("Running DDL statements...")
    cur.execute("ALTER TABLE public.pb_price_events ADD COLUMN IF NOT EXISTS rating NUMERIC(3,2);")
    cur.execute("ALTER TABLE public.pb_price_events ADD COLUMN IF NOT EXISTS reviews INTEGER;")
    cur.execute("ALTER TABLE public.pb_price_events ADD COLUMN IF NOT EXISTS sales_rank INTEGER;")
    cur.execute("ALTER TABLE public.pb_price_events ADD COLUMN IF NOT EXISTS brand TEXT;")
    conn.commit()
    print("Columns rating, reviews, sales_rank, and brand successfully added to public.pb_price_events!")
    
    # Reload schema cache
    print("Reloading PostgREST schema cache...")
    cur.execute("NOTIFY pgrst, 'reload schema';")
    conn.commit()
    print("PostgREST schema cache reload triggered successfully!")

    # Check columns in pb_price_events
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'pb_price_events';")
    cols = cur.fetchall()
    print("Current columns in pb_price_events:")
    for col in cols:
        print(f"  - {col[0]}: {col[1]}")

    cur.close()
    conn.close()
    print("Database connection closed cleanly.")
except Exception as e:
    # Use only safe ASCII characters to print errors
    err_str = str(e).encode('ascii', 'ignore').decode('ascii')
    print(f"[ERROR] Error during database migration: {err_str}")
