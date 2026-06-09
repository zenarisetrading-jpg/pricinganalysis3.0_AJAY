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
        
        print("--- All unique ASINs in bsr_history for s2c_test ---")
        cur.execute("""
            SELECT DISTINCT b.asin, b.category_name, s.parent_asin 
            FROM sc_raw.bsr_history b
            LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
            WHERE b.account_id = 's2c_test'
              AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"BSR ASIN: {r[0]} | Cat: {r[1]} | Sales Traffic Parent: {r[2]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
