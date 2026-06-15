import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def check_bsr_ids():
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT marketplace_id FROM sc_raw.bsr_history")
        print("--- Unique Marketplace IDs in bsr_history ---")
        for row in cur.fetchall():
            print(f"Marketplace ID: {row[0]}")
        
        cur.execute("SELECT DISTINCT account_id FROM sc_raw.bsr_history")
        print("\n--- Unique Account IDs in bsr_history ---")
        for row in cur.fetchall():
            print(f"Account ID: {row[0]}")

    conn.close()

if __name__ == "__main__":
    check_bsr_ids()
