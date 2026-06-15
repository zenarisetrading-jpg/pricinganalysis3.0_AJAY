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
        
        print("--- Unique Account IDs in sc_raw.sales_traffic ---")
        cur.execute("SELECT DISTINCT account_id FROM sc_raw.sales_traffic")
        rows = cur.fetchall()
        for r in rows:
            print(f"Sales Traffic Account ID: {r[0]}")
            
        print("\n--- Sample s2c_test mapping in sales_traffic ---")
        cur.execute("SELECT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE account_id = 's2c_test' LIMIT 10")
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"Child: {r[0]} -> Parent: {r[1]}")
        else:
            print("No rows found in sc_raw.sales_traffic for s2c_test!")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
