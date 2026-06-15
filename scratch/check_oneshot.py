import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_oneshot():
    url = os.getenv("SADDL_DATABASE_URL")
    if not url:
        print("SADDL_DATABASE_URL not found")
        return
    
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE account_id = 'oneshot_uae' AND child_asin != parent_asin LIMIT 20")
        rows = cur.fetchall()
        print(f"oneshot_uae child-parent differences: {rows}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_oneshot()
