import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def final_fix():
    pricing_url = os.getenv("PRICING_DATABASE_URL")
    if not pricing_url: return

    try:
        conn = psycopg2.connect(pricing_url)
        cur = conn.cursor()
        
        # B0F6NHKSQ1 -> B0FNN5WKDG
        # B0FMYLRD2X -> B0FNN5WKDG
        
        for child in ['B0F6NHKSQ1', 'B0FMYLRD2X']:
            print(f"Updating {child} -> B0FNN5WKDG...")
            cur.execute("UPDATE competitor_products SET our_asin = 'B0FNN5WKDG' WHERE our_asin = %s", (child,))
            print(f"   [competitor_products] Rows: {cur.rowcount}")
            
            try:
                cur.execute("UPDATE pricing_analysis SET asin = 'B0FNN5WKDG' WHERE asin = %s", (child,))
                print(f"   [pricing_analysis] Rows: {cur.rowcount}")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                cur.execute("DELETE FROM pricing_analysis WHERE asin = %s", (child,))
                print(f"   [pricing_analysis] Merged duplicate")
            
            try:
                cur.execute("UPDATE pb_client_snapshots_daily SET asin = 'B0FNN5WKDG' WHERE asin = %s", (child,))
                print(f"   [snapshots] Rows: {cur.rowcount}")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                cur.execute("DELETE FROM pb_client_snapshots_daily WHERE asin = %s", (child,))
                print(f"   [snapshots] Merged duplicate")

        conn.commit()
        print("Final fix complete.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_fix()
