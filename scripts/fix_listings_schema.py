import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def fix_schema():
    url = os.environ.get('SADDL_DATABASE_URL').replace('"', '')
    print(f"Connecting to {url.split('@')[-1]}...")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    commands = [
        "ALTER TABLE pb_client_listings ADD COLUMN IF NOT EXISTS strategy TEXT DEFAULT 'mid'",
        "ALTER TABLE pb_client_listings ADD COLUMN IF NOT EXISTS min_price NUMERIC(10, 2)",
        "ALTER TABLE pb_client_listings ADD COLUMN IF NOT EXISTS max_price NUMERIC(10, 2)",
        "ALTER TABLE pb_client_listings ADD COLUMN IF NOT EXISTS category_id TEXT"
    ]
    
    for cmd in commands:
        try:
            cur.execute(cmd)
            print(f"Executed: {cmd}")
        except Exception as e:
            print(f"Error executing {cmd}: {e}")
            conn.rollback()
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Schema fix complete.")

if __name__ == "__main__":
    fix_schema()
