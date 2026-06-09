import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_snapshots():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    
    if not saddl_url or not pricing_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        print("Fetching mappings from SADDL DB...")
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE child_asin IS NOT NULL AND parent_asin IS NOT NULL")
        mappings = saddl_cur.fetchall()
        
        total_updated = 0

        for child, parent in mappings:
            if child == parent: continue
            
            # Update pb_client_snapshots_daily
            try:
                # Note: This might have unique constraint (client_id, asin, snapshot_date)
                pricing_cur.execute(
                    "UPDATE pb_client_snapshots_daily SET asin = %s WHERE asin = %s",
                    (parent, child)
                )
                if pricing_cur.rowcount > 0:
                    print(f"   [snapshots] {child} -> {parent} ({pricing_cur.rowcount} rows)")
                    total_updated += pricing_cur.rowcount
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pb_client_snapshots_daily WHERE asin = %s", (child,))
                print(f"   [snapshots] {child} -> {parent} (Merged duplicate)")
                total_updated += 1
            except Exception as e:
                pricing_conn.rollback()
                print(f"   Error updating snapshots for {child}: {e}")

        pricing_conn.commit()
        print(f"\nTotal snapshots updated: {total_updated}")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    migrate_snapshots()
