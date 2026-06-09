import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def robust_consolidate_saddl():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    if not saddl_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        saddl_cur = saddl_conn.cursor()
        
        account_id = "oneshot_uae"
        
        print(f"Fetching Parent mappings for {account_id}...")
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE account_id = %s AND child_asin != parent_asin", (account_id,))
        mappings = saddl_cur.fetchall()
        print(f"Found {len(mappings)} mappings to process.")

        tables = [
            ("bsr_history", "asin", "account_id"),
            ("sales_traffic", "child_asin", "account_id"),
            ("fba_inventory", "asin", "client_id")
        ]

        for child, parent in mappings:
            print(f"Processing {child} -> {parent}...")
            for table, asin_col, account_col in tables:
                # We do this inside a loop to handle each record properly
                # We use a simple strategy: Try to update. If fail, delete.
                # To avoid transaction rollback, we check for existence or use individual commits
                
                # Check how many rows for this child
                saddl_cur.execute(f"SELECT COUNT(*) FROM sc_raw.{table} WHERE {asin_col} = %s AND {account_col} = %s", (child, account_id))
                child_rows = saddl_cur.fetchone()[0]
                if child_rows == 0: continue
                
                print(f"   [{table}] Found {child_rows} rows for {child}")
                
                # We can't easily merge without knowing the PK. 
                # So we just update and if it fails, we delete.
                # To avoid rolling back everything, we'll do this in a very simple loop or use a more complex SQL.
                
                # Simple SQL: Delete if parent already exists for the same key, then update the rest.
                # This is hard because PKs vary.
                
                # Alternative: Move to a temp table, then insert into original with ON CONFLICT DO NOTHING
                
                # For now, I'll just use individual try-except blocks with commit for each child
                try:
                    saddl_cur.execute(f"UPDATE sc_raw.{table} SET {asin_col} = %s WHERE {asin_col} = %s AND {account_col} = %s", (parent, child, account_id))
                    saddl_conn.commit()
                    print(f"      Updated {saddl_cur.rowcount} rows.")
                except psycopg2.errors.UniqueViolation:
                    saddl_conn.rollback()
                    print(f"      Conflict detected, removing {child} to favor existing {parent} data.")
                    saddl_cur.execute(f"DELETE FROM sc_raw.{table} WHERE {asin_col} = %s AND {account_col} = %s", (child, account_id))
                    saddl_conn.commit()

        print("\n✨ SADDL DATABASE CONSOLIDATION COMPLETE!")

        saddl_cur.close()
        saddl_conn.close()
        
    except Exception as e:
        print(f"Robust Consolidation Error: {e}")

if __name__ == "__main__":
    robust_consolidate_saddl()
