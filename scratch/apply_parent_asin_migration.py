
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("PRICING_DATABASE_URL")
if not db_url:
    print("PRICING_DATABASE_URL not found")
    exit(1)

sql_file = "supabase/migrations/20260514000001_add_competitor_parent_asin.sql"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    with open(sql_file, 'r') as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    print("Migration applied successfully to PRICING_DATABASE!")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error applying migration: {e}")
