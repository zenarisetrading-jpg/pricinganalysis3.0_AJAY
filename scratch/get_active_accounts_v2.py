import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("SADDL_DATABASE_URL")
    if not db_url:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("--- Fetching Active Accounts (Linked to BSR data) ---")
        query = """
        SELECT DISTINCT
            a.account_id,
            a.account_name, 
            a.organization_id,
            a.account_type
        FROM public.accounts a
        JOIN sc_raw.bsr_history b ON a.account_id = b.account_id
        WHERE a.organization_id IS NOT NULL
        ORDER BY a.account_name ASC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        print(f"Active Accounts Found: {len(rows)}")
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}, Org: {row[2]}, Type: {row[3]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
