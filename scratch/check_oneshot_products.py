import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def check_account_products(account_id):
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        query = """
        SELECT DISTINCT asin, category_name, category_id
        FROM sc_raw.bsr_history
        WHERE account_id = %s
        """
        cur.execute(query, (account_id,))
        rows = cur.fetchall()
        print(f"Products for {account_id}:")
        for row in rows:
            print(f"ASIN: {row[0]}, Category Name: {row[1]}, Category ID: {row[2]}")
    conn.close()

if __name__ == "__main__":
    check_account_products("oneshot_uae")
