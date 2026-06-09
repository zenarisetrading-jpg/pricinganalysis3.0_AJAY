import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def final_sku_cleanup():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        pricing_conn = psycopg2.connect(pricing_url)
        pricing_cur = pricing_conn.cursor()
        
        tables_with_sku = [
            ("pb_client_listings", "asin", "sku_id"),
            ("pb_client_snapshots_daily", "asin", "sku_id"),
            ("pb_recommendations", "asin", "sku_id"),
            ("pb_alerts", "asin", "sku_id")
        ]

        print("Updating sku_id to match Parent ASIN...")
        for table, asin_col, sku_col in tables_with_sku:
            pricing_cur.execute(f"UPDATE {table} SET {sku_col} = {asin_col} WHERE {sku_col} != {asin_col}")
            if pricing_cur.rowcount > 0:
                print(f"   [{table}] Updated {pricing_cur.rowcount} SKU IDs to match Parent ASIN.")
        
        pricing_conn.commit()
        print("\n✨ ALL SKU IDs ARE NOW PARENT-CENTRIC!")

        pricing_cur.close()
        pricing_conn.close()
        
    except Exception as e:
        print(f"Cleanup Error: {e}")

if __name__ == "__main__":
    final_sku_cleanup()
