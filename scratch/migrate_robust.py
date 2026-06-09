import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_data():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    
    if not saddl_url or not pricing_url:
        print("Database URLs not found in .env")
        return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        print("Fetching ALL mappings from SADDL DB...")
        # Get every unique child-to-parent mapping
        saddl_cur.execute("SELECT DISTINCT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE child_asin IS NOT NULL AND parent_asin IS NOT NULL")
        mappings = saddl_cur.fetchall()
        print(f"Found {len(mappings)} unique mappings.")

        total_competitor_updated = 0
        total_analysis_updated = 0

        for child, parent in mappings:
            if child == parent: continue
            
            # Update competitor_products
            pricing_cur.execute(
                "UPDATE competitor_products SET our_asin = %s WHERE our_asin = %s",
                (parent, child)
            )
            if pricing_cur.rowcount > 0:
                print(f"   [competitor_products] {child} -> {parent} ({pricing_cur.rowcount} rows)")
                total_competitor_updated += pricing_cur.rowcount

            # Update pricing_analysis
            try:
                pricing_cur.execute(
                    "UPDATE pricing_analysis SET asin = %s WHERE asin = %s",
                    (parent, child)
                )
                if pricing_cur.rowcount > 0:
                    print(f"   [pricing_analysis] {child} -> {parent} ({pricing_cur.rowcount} rows)")
                    total_analysis_updated += pricing_cur.rowcount
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pricing_analysis WHERE asin = %s", (child,))
                print(f"   [pricing_analysis] {child} -> {parent} (Merged duplicate)")
                total_analysis_updated += 1
            except Exception as e:
                pricing_conn.rollback()
                print(f"   Error updating analysis for {child}: {e}")

        pricing_conn.commit()
        print(f"\nFinal Totals:")
        print(f"- Competitor rows updated: {total_competitor_updated}")
        print(f"- Analysis records updated: {total_analysis_updated}")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    migrate_data()
