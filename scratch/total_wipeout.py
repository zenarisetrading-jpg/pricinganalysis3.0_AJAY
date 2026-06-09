import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def total_wipeout():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        target = 'B0F6NHKSQ1'
        parent = 'B0FNN5WKDG'
        
        # 1. Count before
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = %s", (target,))
        before = cur.fetchone()[0]
        print(f"Before: {target} has {before} rows in competitor_products.")
        
        # 2. Update with TRIM to be super safe
        cur.execute("UPDATE competitor_products SET our_asin = %s WHERE TRIM(our_asin) = %s", (parent, target))
        print(f"Update: {cur.rowcount} rows changed.")
        
        # 3. Count after
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = %s", (target,))
        after = cur.fetchone()[0]
        print(f"After: {target} has {after} rows in competitor_products.")
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    total_wipeout()
