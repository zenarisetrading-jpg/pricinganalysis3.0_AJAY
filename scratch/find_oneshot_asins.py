
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def find_mapping_table():
    if not SADDL_DATABASE_URL:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(SADDL_DATABASE_URL)
        with conn.cursor() as cur:
            # 1. List all tables in 'public' and 'sc_raw' to find mapping tables
            print("Searching for mapping tables...")
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema IN ('public', 'sc_raw') AND table_name ILIKE '%amazon%'")
            tables = [t[0] for t in cur.fetchall()]
            print(f"Potential mapping tables: {tables}")
            
            # 2. Check sc_raw.bsr_history to see what marketplace_id is used there
            print("\nChecking sc_raw.bsr_history marketplace_id sample:")
            cur.execute("SELECT DISTINCT marketplace_id FROM sc_raw.bsr_history LIMIT 5")
            print(f"BSR Marketplace IDs: {[r[0] for r in cur.fetchall()]}")

            # 3. Check for specific ASINs in bsr_history to work backwards
            print("\nChecking for any recent products in oneshot_uae (BSR history)...")
            cur.execute("SELECT asin, category_name FROM sc_raw.bsr_history WHERE marketplace_id = 'oneshot_uae' LIMIT 5")
            bsr_oneshot = cur.fetchall()
            if bsr_oneshot:
                print(f"Found products using 'oneshot_uae' ID in BSR history!")
                for b in bsr_oneshot:
                    print(f"ASIN: {b[0]} | Category: {b[1]}")
            else:
                print("No records found for 'oneshot_uae' in BSR history.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_mapping_table()
