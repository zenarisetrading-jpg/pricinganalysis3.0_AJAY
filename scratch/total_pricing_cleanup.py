import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def final_pricing_db_cleanup():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    
    if not saddl_url or not pricing_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        print("Fetching mappings from SADDL DB...")
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin, account_id FROM sc_raw.sales_traffic WHERE child_asin != parent_asin")
        mappings = saddl_cur.fetchall()
        print(f"Found {len(mappings)} mappings.")

        tables = [
            ("pb_client_listings", "asin", "client_id"),
            ("pb_client_snapshots_daily", "asin", "client_id"),
            ("competitor_products", "our_asin", None), 
            ("pricing_analysis", "asin", None), # No client_id/account_id
            ("pb_recommendations", "asin", "client_id"),
            ("pb_alerts", "asin", "client_id")
        ]

        for child, parent, account in mappings:
            for table, asin_col, account_col in tables:
                try:
                    if account_col:
                        # Only update for the specific account if the column exists
                        pricing_cur.execute(f"UPDATE {table} SET {asin_col} = %s WHERE {asin_col} = %s AND {account_col} = %s", (parent, child, account))
                    else:
                        # Global update if no account column
                        pricing_cur.execute(f"UPDATE {table} SET {asin_col} = %s WHERE {asin_col} = %s", (parent, child))
                    
                    if pricing_cur.rowcount > 0:
                        print(f"   [{table}] {child} -> {parent} ({pricing_cur.rowcount} rows)")
                except psycopg2.errors.UniqueViolation:
                    pricing_conn.rollback()
                    if account_col:
                        pricing_cur.execute(f"DELETE FROM {table} WHERE {asin_col} = %s AND {account_col} = %s", (child, account))
                    else:
                        pricing_cur.execute(f"DELETE FROM {table} WHERE {asin_col} = %s", (child,))
                    print(f"   [{table}] {child} -> {parent} (Merged duplicate)")

            pricing_conn.commit()

        print("\n✨ ALL PRICING DB TABLES ARE NOW PARENT-CENTRIC!")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Cleanup Error: {e}")

if __name__ == "__main__":
    final_pricing_db_cleanup()
