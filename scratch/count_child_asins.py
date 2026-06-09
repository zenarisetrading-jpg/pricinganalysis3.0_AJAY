import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("SADDL_DATABASE_URL")
    if not db_url:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        category_id = "17007680031" # Sports Water Bottles
        
        for account in ["s2c_test", "s2c_uae_test"]:
            print(f"\n--- Counting child ASINs in Sports Water Bottles for '{account}' ---")
            
            # Query active products matching the category in SADDL catalog
            query = """
                SELECT DISTINCT b.asin, COALESCE(s.parent_asin, b.asin) as parent_asin
                FROM sc_raw.bsr_history b
                LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
                WHERE b.account_id = %s
                  AND b.category_id = %s
                  AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history);
            """
            cur.execute(query, (account, category_id))
            rows = cur.fetchall()
            
            print(f"Total Child ASINs matching Sports Water Bottles (Category ID: {category_id}): {len(rows)}")
            for idx, r in enumerate(rows, 1):
                print(f"  {idx}. Child: {r[0]} | Parent: {r[1]}")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
