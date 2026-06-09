
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")
TARGET_IDS = ['A2VIGQ35RCS4UG', 'A17E79C6D8DWNP']

def find_missing_products():
    if not SADDL_DATABASE_URL:
        print("❌ SADDL_DATABASE_URL not set")
        return

    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        # Check bsr_history (current source)
        cur.execute("SELECT COUNT(DISTINCT asin) FROM sc_raw.bsr_history WHERE marketplace_id = ANY(%s)", (TARGET_IDS,))
        bsr_count = cur.fetchone()[0]
        
        # Check sales_report (more likely to have all products)
        try:
            cur.execute("SELECT COUNT(DISTINCT asin) FROM sc_raw.sales_report WHERE marketplace_id = ANY(%s)", (TARGET_IDS,))
            sales_count = cur.fetchone()[0]
        except:
            sales_count = "N/A"
            conn.rollback()

        # Check inventory
        try:
            cur.execute("SELECT COUNT(DISTINCT asin) FROM sc_raw.inventory WHERE seller_id = ANY(%s)", (TARGET_IDS,))
            inv_count = cur.fetchone()[0]
        except:
            inv_count = "N/A"
            conn.rollback()

        print(f"📊 Product counts for {TARGET_IDS}:")
        print(f"  - In BSR History: {bsr_count}")
        print(f"  - In Sales Report: {sales_count}")
        print(f"  - In Inventory: {inv_count}")

    conn.close()

if __name__ == "__main__":
    find_missing_products()
