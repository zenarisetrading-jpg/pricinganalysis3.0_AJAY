import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_asins():
    url = os.getenv("PRICING_DATABASE_URL")
    asins = ['B0CZBWV963', 'B0CZC7Z3JN', 'B0CZCB2PZY', 'B0CZBXGPVH']
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT parent_asin FROM competitor_products WHERE parent_asin = ANY(%s)", (asins,))
        print(f"Competitor Products parents found: {cur.fetchall()}")
        cur.execute("SELECT asin FROM pricing_analysis WHERE asin = ANY(%s)", (asins,))
        print(f"Pricing Analysis asins found: {cur.fetchall()}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_asins()
