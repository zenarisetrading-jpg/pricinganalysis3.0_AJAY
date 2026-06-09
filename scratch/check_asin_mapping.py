import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("SADDL_DATABASE_URL")
    if not db_url: return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check a sample of ASIN to Parent ASIN mapping
        query = """
        SELECT asin, parent_asin 
        FROM sc_raw.sales_traffic 
        WHERE account_id = 's2c_uae_test' -- Using a known account from previous diag
        LIMIT 10
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        print("Sample ASIN to Parent ASIN mapping:")
        for r in rows:
            print(f"- Child: {r[0]} -> Parent: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
