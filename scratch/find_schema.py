import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def find_schema(table_name):
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(f"SELECT table_schema FROM information_schema.tables WHERE table_name = '{table_name}'")
        rows = cur.fetchall()
        print(f"Table {table_name} found in schemas: {[r[0] for r in rows]}")
    conn.close()

if __name__ == "__main__":
    find_schema("product_catalog")
