import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_saddl():
    url = os.getenv("SADDL_DATABASE_URL")
    if not url:
        print("SADDL_DATABASE_URL not found")
        return
    
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT child_asin FROM sc_raw.sales_traffic WHERE parent_asin = 'B0CZBWV963'")
        rows = cur.fetchall()
        print(f"SADDL children for B0CZBWV963: {rows}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_saddl()
