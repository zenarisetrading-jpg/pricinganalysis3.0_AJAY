import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_last_tables():
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

        for child, parent, account in mappings:
            # 1. pb_recommendations
            try:
                pricing_cur.execute("UPDATE pb_recommendations SET asin = %s WHERE asin = %s AND client_id = %s", (parent, child, account))
                if pricing_cur.rowcount > 0:
                    print(f"   [pb_recommendations] {child} -> {parent} ({pricing_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pb_recommendations WHERE asin = %s AND client_id = %s", (child, account))
                print(f"   [pb_recommendations] {child} -> {parent} (Merged duplicate)")

            # 2. pb_alerts
            try:
                pricing_cur.execute("UPDATE pb_alerts SET asin = %s WHERE asin = %s AND client_id = %s", (parent, child, account))
                if pricing_cur.rowcount > 0:
                    print(f"   [pb_alerts] {child} -> {parent} ({pricing_cur.rowcount} rows)")
            except psycopg2.errors.UniqueViolation:
                pricing_conn.rollback()
                pricing_cur.execute("DELETE FROM pb_alerts WHERE asin = %s AND client_id = %s", (child, account))
                print(f"   [pb_alerts] {child} -> {parent} (Merged duplicate)")

            pricing_conn.commit()

        print("\n✨ FINAL TABLES MIGRATED!")

        saddl_cur.close()
        pricing_cur.close()
        saddl_conn.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    migrate_last_tables()
