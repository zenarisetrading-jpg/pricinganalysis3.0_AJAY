import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_schemas():
    db_url = os.getenv("PRICING_DATABASE_URL")
    if not db_url: return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("Tables in PRICING_DATABASE_URL:")
        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"- {r[0]}.{r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schemas()
