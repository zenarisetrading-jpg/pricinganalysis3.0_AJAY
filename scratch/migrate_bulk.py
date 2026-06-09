import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def bulk_migrate():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    
    if not saddl_url or not pricing_url: return

    try:
        saddl_conn = psycopg2.connect(saddl_url)
        pricing_conn = psycopg2.connect(pricing_url)
        
        saddl_cur = saddl_conn.cursor()
        pricing_cur = pricing_conn.cursor()
        
        # 1. Create a mapping table in SADDL to speed up joins
        print("Creating temporary mapping table in SADDL...")
        saddl_cur.execute("""
            CREATE TEMP TABLE asin_mapping AS
            SELECT DISTINCT child_asin, parent_asin, account_id
            FROM sc_raw.sales_traffic
            WHERE child_asin != parent_asin;
        """)
        
        # 2. Bulk Deduplicate bsr_history
        print("Deduplicating bsr_history (removing child rows where parent record exists)...")
        saddl_cur.execute("""
            DELETE FROM sc_raw.bsr_history b
            USING asin_mapping m
            WHERE b.asin = m.child_asin
              AND b.account_id = m.account_id
              AND EXISTS (
                  SELECT 1 FROM sc_raw.bsr_history p
                  WHERE p.asin = m.parent_asin
                    AND p.account_id = m.account_id
                    AND p.report_date = b.report_date
                    AND p.marketplace_id = b.marketplace_id
                    AND p.category_id = b.category_id
              );
        """)
        print(f"   Deleted {saddl_cur.rowcount} duplicate child rows.")

        # 3. Bulk Update bsr_history
        print("Updating remaining child rows to parent ASIN in bsr_history...")
        saddl_cur.execute("""
            UPDATE sc_raw.bsr_history b
            SET asin = m.parent_asin
            FROM asin_mapping m
            WHERE b.asin = m.child_asin
              AND b.account_id = m.account_id;
        """)
        print(f"   Updated {saddl_cur.rowcount} child rows to Parent ASIN.")

        saddl_conn.commit()

        # 4. Now handle Pricing DB (Supabase)
        # We'll fetch the mapping to memory as it's smaller
        print("Fetching mappings for Pricing DB...")
        saddl_cur.execute("SELECT child_asin, parent_asin, account_id FROM asin_mapping")
        mappings = saddl_cur.fetchall()
        
        # Create temp table in Pricing DB
        print("Creating temporary mapping table in Pricing DB...")
        pricing_cur.execute("CREATE TEMP TABLE asin_mapping (child_asin text, parent_asin text, account_id text)")
        from psycopg2.extras import execute_values
        execute_values(pricing_cur, "INSERT INTO asin_mapping (child_asin, parent_asin, account_id) VALUES %s", mappings)

        # 5. Bulk Update competitor_products
        print("Bulk updating competitor_products...")
        pricing_cur.execute("""
            UPDATE competitor_products c
            SET our_asin = m.parent_asin
            FROM asin_mapping m
            WHERE c.our_asin = m.child_asin;
        """)
        print(f"   Updated {pricing_cur.rowcount} rows in competitor_products.")

        # 6. Bulk Deduplicate & Update listings
        print("Handling listings (dedup and update)...")
        pricing_cur.execute("""
            DELETE FROM pb_client_listings b
            USING asin_mapping m
            WHERE b.asin = m.child_asin
              AND b.client_id = m.account_id
              AND EXISTS (
                  SELECT 1 FROM pb_client_listings p
                  WHERE p.asin = m.parent_asin
                    AND p.client_id = m.account_id
              );
        """)
        print(f"   Deleted {pricing_cur.rowcount} duplicate listings.")
        
        pricing_cur.execute("""
            UPDATE pb_client_listings b
            SET asin = m.parent_asin
            FROM asin_mapping m
            WHERE b.asin = m.child_asin
              AND b.client_id = m.account_id;
        """)
        print(f"   Updated {pricing_cur.rowcount} listings to Parent ASIN.")

        pricing_conn.commit()
        print("\n✨ BULK MIGRATION COMPLETE!")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Bulk Migration Error: {e}")

if __name__ == "__main__":
    bulk_migrate()
