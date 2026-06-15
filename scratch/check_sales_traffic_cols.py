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
        
        query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'sc_raw' AND table_name = 'sales_traffic'
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        print("Columns in sc_raw.sales_traffic:")
        for r in rows:
            print(f"- {r[0]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
