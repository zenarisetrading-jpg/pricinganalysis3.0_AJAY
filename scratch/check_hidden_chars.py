import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_hidden():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        print("Checking for hidden characters in B0F6NHKSQ1...")
        cur.execute("SELECT our_asin, LENGTH(our_asin) FROM competitor_products WHERE our_asin LIKE '%B0F6NHKSQ1%' LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            print(f"- '{r[0]}' | Length: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_hidden()
