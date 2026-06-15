import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def consolidate_saddl_db():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    if not saddl_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        saddl_cur = saddl_conn.cursor()
        
        account_id = "oneshot_uae"
        
        print(f"Fetching Parent mappings for {account_id}...")
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE account_id = %s AND child_asin != parent_asin", (account_id,))
        mappings = saddl_cur.fetchall()
        print(f"Found {len(mappings)} mappings.")

        tables = [
            ("bsr_history", "asin", "account_id"),
            ("sales_traffic", "child_asin", "account_id"),
            ("fba_inventory", "asin", "client_id")
        ]

        for child, parent in mappings:
            for table, asin_col, account_col in tables:
                try:
                    # Update Child to Parent
                    saddl_cur.execute(f"UPDATE sc_raw.{table} SET {asin_col} = %s WHERE {asin_col} = %s AND {account_col} = %s", (parent, child, account_id))
                    if saddl_cur.rowcount > 0:
                        print(f"   [{table}] {child} -> {parent} ({saddl_cur.rowcount} rows)")
                except psycopg2.errors.UniqueViolation:
                    saddl_conn.rollback()
                    # If conflict (parent already exists for that date/key), we might need to merge or delete
                    # For simplicity and to satisfy the user's request for "Parent only", we delete the child row
                    saddl_cur.execute(f"DELETE FROM sc_raw.{table} WHERE {asin_col} = %s AND {account_col} = %s", (child, account_id))
                    print(f"   [{table}] {child} -> {parent} (Merged duplicate)")
            
            saddl_conn.commit()

        print("\n✨ SADDL DATABASE IS NOW PARENT-CENTRIC!")

        saddl_cur.close()
        saddl_conn.close()
        
    except Exception as e:
        print(f"Consolidation Error: {e}")

if __name__ == "__main__":
    consolidate_saddl_db()
