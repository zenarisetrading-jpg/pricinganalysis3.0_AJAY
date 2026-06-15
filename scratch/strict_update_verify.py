import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def strict_update():
    url = os.getenv("PRICING_DATABASE_URL")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        target = 'B0CZLKLJX5'
        parent = 'B0FNN5WKDG'
        
        print(f"1. Checking initial count for {target}...")
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = %s", (target,))
        print(f"   Count: {cur.fetchone()[0]}")
        
        print(f"2. Updating {target} -> {parent}...")
        cur.execute("UPDATE competitor_products SET our_asin = %s WHERE our_asin = %s", (parent, target))
        print(f"   Rows affected: {cur.rowcount}")
        
        print("3. Committing transaction...")
        conn.commit()
        
        print(f"4. Re-checking count for {target} AFTER commit...")
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = %s", (target,))
        print(f"   Count: {cur.fetchone()[0]}")
        
        cur.close()
        conn.close()
        
        # Open a completely NEW connection to see if it stuck
        print("\n5. Opening a NEW connection to verify persistence...")
        conn2 = psycopg2.connect(url)
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = %s", (target,))
        final_count = cur2.fetchone()[0]
        print(f"   Final Count in NEW connection: {final_count}")
        cur2.close()
        conn2.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    strict_update()
