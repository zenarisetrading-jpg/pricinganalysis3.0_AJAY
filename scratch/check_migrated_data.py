import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_data():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        print("Checking 'competitor_products' for Parent ASINs in 'our_asin' column:")
        cur.execute("SELECT our_asin, competitor_asin, scraped_at FROM competitor_products ORDER BY scraped_at DESC LIMIT 10")
        rows = cur.fetchall()
        
        for r in rows:
            print(f"- our_asin: {r[0]} | competitor: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
