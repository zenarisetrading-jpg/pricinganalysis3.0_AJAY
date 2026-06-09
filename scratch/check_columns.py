import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def get_columns(table_name):
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Columns for {table_name}: {cols}")
    conn.close()

if __name__ == "__main__":
    get_columns("product_catalog")
    get_columns("bsr_history")
