import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_both():
    s_url = os.getenv("SADDL_DATABASE_URL")
    p_url = os.getenv("PRICING_DATABASE_URL")
    
    parents = ['B0CZBWV963', 'B0D8N3P5XX', 'B0F92Y9GGD', 'B0FN4NK1Z5', 'B0B1X3D9HZ']
    
    print("--- Checking Competitor Products ---")
    try:
        conn = psycopg2.connect(p_url)
        cur = conn.cursor()
        cur.execute("SELECT parent_asin, product_asins FROM competitor_products WHERE parent_asin = ANY(%s) LIMIT 10", (parents,))
        rows = cur.fetchall()
        for row in rows:
            print(f"Parent: {row[0]}, Product ASINs: {row[1]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking pricing: {e}")

if __name__ == "__main__":
    check_both()
