import sys
import os
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

def run_migration():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return
        
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Adding seller_name to pb_price_events...")
        cur.execute("ALTER TABLE public.pb_price_events ADD COLUMN IF NOT EXISTS seller_name TEXT;")
        
        print("✅ Migration successful!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
