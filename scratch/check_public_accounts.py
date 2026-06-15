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
        
        print("--- Accounts in public.accounts ---")
        try:
            cur.execute("SELECT account_id, account_name FROM public.accounts")
            rows = cur.fetchall()
            for r in rows:
                print(f"ID: {r[0]} | Name: {r[1]}")
        except Exception as e:
            print(f"Error querying public.accounts: {e}")
            conn.rollback()

        print("\n--- Unique Account IDs in sc_raw.bsr_history ---")
        try:
            cur.execute("SELECT DISTINCT account_id FROM sc_raw.bsr_history")
            rows = cur.fetchall()
            for r in rows:
                print(f"BSR Account ID: {r[0]}")
        except Exception as e:
            print(f"Error querying sc_raw.bsr_history: {e}")
            conn.rollback()

        print("\n--- Unique Category Names in sc_raw.bsr_history ---")
        try:
            cur.execute("SELECT DISTINCT category_name FROM sc_raw.bsr_history LIMIT 30")
            rows = cur.fetchall()
            print("Found categories (limit 30):")
            for r in rows:
                print(f"- {r[0]}")
        except Exception as e:
            print(f"Error querying sc_raw.bsr_history categories: {e}")
            conn.rollback()

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
