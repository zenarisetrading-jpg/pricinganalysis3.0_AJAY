import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_count():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = 'B0FFB2F46C'")
        count = cur.fetchone()[0]
        print(f"Rows for B0FFB2F46C (Child): {count}")
        
        cur.execute("SELECT COUNT(*) FROM competitor_products WHERE our_asin = 'B0FNN5WKDG'")
        p_count = cur.fetchone()[0]
        print(f"Rows for B0FNN5WKDG (Parent): {p_count}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_count()
