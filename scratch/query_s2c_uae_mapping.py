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
        
        # Test for both s2c_uae and s2c_uae_test
        for account in ["s2c_uae_test", "s2c_uae"]:
            print(f"\n--- Parent & Child ASINs for account_id: '{account}' ---")
            query = """
                SELECT DISTINCT 
                    parent_asin, 
                    child_asin
                FROM sc_raw.sales_traffic
                WHERE account_id = %s
                ORDER BY parent_asin, child_asin;
            """
            cur.execute(query, (account,))
            rows = cur.fetchall()
            if rows:
                print(f"Found {len(rows)} mappings:")
                for r in rows:
                    print(f"Parent ASIN: {r[0]} | Child ASIN: {r[1]}")
            else:
                print("No mappings found.")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
