import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add parent dir to path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

def explore_saddl_db():
    if not SADDL_DATABASE_URL:
        print("SADDL_DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(SADDL_DATABASE_URL)
        with conn.cursor() as cur:
            print("--- SCHEMAS ---")
            cur.execute("SELECT schema_name FROM information_schema.schemata")
            for row in cur.fetchall():
                print(f"Schema: {row[0]}")

            print("\n--- TABLES in public ---")
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            for row in cur.fetchall():
                print(f"Table: {row[0]}")

            print("\n--- TABLES in sc_raw ---")
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'sc_raw'")
            for row in cur.fetchall():
                print(f"Table: {row[0]}")
                
            # Check for products table
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%product%'")
            print("\n--- PRODUCT TABLES ---")
            for row in cur.fetchall():
                print(f"Found product table: {row[0]}")

        conn.close()
    except Exception as e:
        print(f"Error exploring SADDL DB: {e}")

if __name__ == "__main__":
    explore_saddl_db()
