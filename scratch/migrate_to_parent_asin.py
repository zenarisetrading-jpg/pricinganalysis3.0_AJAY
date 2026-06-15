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
        # 1. Connect to both databases
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        print("Connecting: Fetching Child-to-Parent mapping from SADDL DB...")
        # Get mapping for all accounts
        saddl_cur.execute("SELECT child_asin, parent_asin, account_id FROM sc_raw.sales_traffic")
        mapping = saddl_cur.fetchall()
        
        # Create a dictionary for fast lookup: (child_asin, account_id) -> parent_asin
        asin_map = { (r[0], r[2]): r[1] for r in mapping if r[0] and r[1] }
        
        print(f"Success: Found {len(asin_map)} mappings.")

        # 2. Update competitor_products table
        print("Updating: 'competitor_products' table...")
        pricing_cur.execute("SELECT DISTINCT our_asin FROM competitor_products")
        existing_asins = [r[0] for r in pricing_cur.fetchall()]
        
        updated_count = 0
        for child_asin in existing_asins:
            parent_asin = None
            for (c, acc), p in asin_map.items():
                if c == child_asin:
                    parent_asin = p
                    break
            
            if parent_asin and parent_asin != child_asin:
                pricing_cur.execute(
                    "UPDATE competitor_products SET our_asin = %s WHERE our_asin = %s",
                    (parent_asin, child_asin)
                )
                updated_count += pricing_cur.rowcount
        
        print(f"Success: Updated {updated_count} rows in 'competitor_products'.")

        # 3. Update pricing_analysis table
        print("Updating: 'pricing_analysis' table...")
        pricing_cur.execute("SELECT asin FROM pricing_analysis")
        analysis_asins = [r[0] for r in pricing_cur.fetchall()]
        
        analysis_updated = 0
        for child_asin in analysis_asins:
            parent_asin = None
            for (c, acc), p in asin_map.items():
                if c == child_asin:
                    parent_asin = p
                    break
            
            if parent_asin and parent_asin != child_asin:
                try:
                    pricing_cur.execute(
                        "UPDATE pricing_analysis SET asin = %s WHERE asin = %s",
                        (parent_asin, child_asin)
                    )
                    analysis_updated += pricing_cur.rowcount
                except psycopg2.errors.UniqueViolation:
                    pricing_conn.rollback()
                    # If it already exists, just delete the child record
                    pricing_cur.execute("DELETE FROM pricing_analysis WHERE asin = %s", (child_asin,))
                    analysis_updated += 1
                    print(f"   Merged duplicate: {child_asin} -> {parent_asin}")
                except Exception as e:
                    pricing_conn.rollback()
                    print(f"   Error updating {child_asin}: {e}")

        pricing_conn.commit()
        print(f"Success: Updated {analysis_updated} records in 'pricing_analysis'.")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
        print("\nMigration complete! Your database now uses Parent ASINs.")

    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    migrate_data()
