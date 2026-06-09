
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def explore_oneshot_mapping():
    if not SADDL_DATABASE_URL:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(SADDL_DATABASE_URL)
        with conn.cursor() as cur:
            # 1. Search for 'oneshot' in the accounts metadata
            print("Searching accounts metadata...")
            cur.execute("SELECT account_id, metadata FROM public.accounts WHERE account_name ILIKE '%oneshot%'")
            results = cur.fetchall()
            for rid, meta in results:
                print(f"Account: {rid} | Meta: {meta}")

            # 2. Check for a credentials or mapping table
            print("\nChecking for common mapping tables...")
            tables_to_check = ['public.credentials', 'public.amazon_accounts', 'public.profiles', 'public.seller_mappings']
            for table in tables_to_check:
                try:
                    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table.split('.')[1]}'")
                    cols = [c[0] for c in cur.fetchall()]
                    if cols:
                        print(f"Table {table} exists with columns: {cols}")
                        # Look for 'oneshot' in those tables
                        search_cols = [c for c in cols if 'id' in c.lower() or 'name' in c.lower() or 'account' in c.lower()]
                        if search_cols:
                            query = f"SELECT * FROM {table} WHERE " + " OR ".join([f"CAST({c} AS TEXT) ILIKE '%oneshot%'" for c in search_cols])
                            cur.execute(query)
                            rows = cur.fetchall()
                            if rows:
                                print(f"Found match in {table}: {rows}")
                except:
                    continue

            # 3. Find the Marketplace ID that has the MOST data
            print("\nTop 5 Marketplace IDs by record count in sales_traffic:")
            cur.execute("SELECT marketplace_id, COUNT(*) as cnt FROM sc_raw.sales_traffic GROUP BY marketplace_id ORDER BY cnt DESC LIMIT 5")
            for r in cur.fetchall():
                print(f"ID: {r[0]} | Records: {r[1]}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore_oneshot_mapping()
