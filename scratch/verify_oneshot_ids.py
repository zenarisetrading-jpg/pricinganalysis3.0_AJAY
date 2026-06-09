import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def verify_ids():
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        # Check OneShot IDs
        cur.execute("SELECT account_id, account_name FROM public.accounts WHERE account_id IN ('A2VIGQ35RCS4UG', 'A17E79C6D8DWNP', 'oneshot_uae')")
        print("--- Account Names for OneShot IDs ---")
        for row in cur.fetchall():
            print(f"ID: {row[0]} | Name: {row[1]}")
        
        # Check if there are other accounts
        cur.execute("SELECT account_id, account_name FROM public.accounts LIMIT 20")
        print("\n--- Other Accounts (Sample) ---")
        for row in cur.fetchall():
            print(f"ID: {row[0]} | Name: {row[1]}")

    conn.close()

if __name__ == "__main__":
    verify_ids()
