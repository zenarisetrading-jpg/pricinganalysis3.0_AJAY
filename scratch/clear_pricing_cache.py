import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
PRICING_DATABASE_URL = os.getenv("PRICING_DATABASE_URL")

def clear_cache():
    print("Connecting to Pricing Database...")
    try:
        conn = psycopg2.connect(PRICING_DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        tables = ["pricing_analysis", "pb_recommendations", "pb_alerts"]
        for t in tables:
            print(f"Clearing table: {t}...")
            cur.execute(f"DELETE FROM {t}")
            print(f"Cleared {cur.rowcount} rows from {t}.")
            
        cur.close()
        conn.close()
        print("Successfully cleared all pricing analysis cache!")
    except Exception as e:
        print(f"Error clearing cache: {e}")

if __name__ == "__main__":
    clear_cache()
