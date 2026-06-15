import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_everything():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    
    if not saddl_url or not pricing_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        print("Fetching ALL mappings from SADDL DB...")
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE child_asin IS NOT NULL AND parent_asin IS NOT NULL")
        mappings = saddl_cur.fetchall()
        print(f"Found {len(mappings)} mappings.")

        for child, parent in mappings:
            if child == parent: continue
            
            # --- SADDL DB ---
            # 1. sc_raw.bsr_history
            try:
                saddl_cur.execute("UPDATE sc_raw.bsr_history SET asin = %s WHERE asin = %s", (parent, child))
                if saddl_cur.rowcount > 0:
                    print(f"   [SADDL bsr_history] {child} -> {parent} ({saddl_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                saddl_conn.rollback()
                # If unique violation, it means parent already exists for those dates/categories.
                # We'll just delete the child records as they are redundant now.
                saddl_cur.execute("DELETE FROM sc_raw.bsr_history WHERE asin = %s", (child,))
                print(f"   [SADDL bsr_history] {child} -> {parent} (Merged duplicate)")
            
            # --- PRICING DB ---
            # 2. pb_client_listings
            try:
                pricing_cur.execute("UPDATE pb_client_listings SET asin = %s WHERE asin = %s", (parent, child))
                if pricing_cur.rowcount > 0:
                    print(f"   [PRICING listings] {child} -> {parent} ({pricing_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pb_client_listings WHERE asin = %s", (child,))
                print(f"   [PRICING listings] {child} -> {parent} (Merged duplicate)")

            # 3. pb_client_snapshots_daily
            try:
                pricing_cur.execute("UPDATE pb_client_snapshots_daily SET asin = %s WHERE asin = %s", (parent, child))
                if pricing_cur.rowcount > 0:
                    print(f"   [PRICING snapshots] {child} -> {parent} ({pricing_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pb_client_snapshots_daily WHERE asin = %s", (child,))
                print(f"   [PRICING snapshots] {child} -> {parent} (Merged duplicate)")

            # 4. competitor_products
            pricing_cur.execute("UPDATE competitor_products SET our_asin = %s WHERE our_asin = %s", (parent, child))
            if pricing_cur.rowcount > 0:
                print(f"   [PRICING competitors] {child} -> {parent} ({pricing_cur.rowcount} rows)")

            # 5. pricing_analysis
            try:
                pricing_cur.execute("UPDATE pricing_analysis SET asin = %s WHERE asin = %s", (parent, child))
                if pricing_cur.rowcount > 0:
                    print(f"   [PRICING analysis] {child} -> {parent} ({pricing_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pricing_analysis WHERE asin = %s", (child,))
                print(f"   [PRICING analysis] {child} -> {parent} (Merged duplicate)")

            # Commit after each child
            saddl_conn.commit()
            pricing_conn.commit()

        print("\n✨ TOTAL MIGRATION COMPLETE! Everything is now Parent-centric.")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    migrate_everything()
