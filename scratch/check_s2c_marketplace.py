import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("SADDL_DATABASE_URL")
    if not db_url:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("--- s2c_test products marketplace_id check ---")
        cur.execute("""
            SELECT DISTINCT marketplace_id 
            FROM sc_raw.bsr_history 
            WHERE account_id = 's2c_test'
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"Marketplace ID in BSR: {r[0]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
