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
        
        print("--- Listing all schemas ---")
        cur.execute("SELECT schema_name FROM information_schema.schemata")
        schemas = cur.fetchall()
        for schema in schemas:
            print(f"Schema: {schema[0]}")
            
        print("\n--- Listing Tables in all schemas (excluding system schemas) ---")
        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
        """)
        tables = cur.fetchall()
        for table in tables:
            print(f"Schema: {table[0]}, Table: {table[1]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
