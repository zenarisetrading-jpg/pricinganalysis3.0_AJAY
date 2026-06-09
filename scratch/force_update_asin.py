import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def force_update():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        print("Forcing update for B0FFB2F46C -> B0FNN5WKDG...")
        cur.execute(
            "UPDATE competitor_products SET our_asin = 'B0FNN5WKDG' WHERE our_asin = 'B0FFB2F46C'"
        )
        print(f"Rows updated: {cur.rowcount}")
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    force_update()
