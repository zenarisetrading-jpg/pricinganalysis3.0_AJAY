import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_mapping():
    saddl_url = os.getenv("SADDL_DATABASE_URL")
    if not saddl_url: return

    try:
        conn = psycopg2.connect(saddl_url)
        cur = conn.cursor()
        
        print("Checking mappings in SADDL DB:")
        cur.execute("SELECT child_asin, parent_asin FROM sc_raw.sales_traffic WHERE child_asin IN ('B0FMYLRD2X', 'B0F6NHKSQ1')")
        rows = cur.fetchall()
        
        for r in rows:
            print(f"- child: {r[0]} | parent: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_mapping()
