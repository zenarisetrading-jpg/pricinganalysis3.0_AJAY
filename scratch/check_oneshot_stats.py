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
        
        # Count total Child ASINs vs Unique Parent ASINs for oneshot-uae
        query = """
        SELECT 
            COUNT(DISTINCT child_asin) as total_children,
            COUNT(DISTINCT parent_asin) as total_parents
        FROM sc_raw.sales_traffic 
        WHERE account_id = 'oneshot_uae'
        """
        cur.execute(query)
        r = cur.fetchone()
        
        print(f"oneshot-uae Stats:")
        print(f"- Total Child ASINs: {r[0]}")
        print(f"- Unique Parent ASINs: {r[1]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
