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
        
        print("--- Searching for pb_clients in all schemas ---")
        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'pb_clients'
        """)
        tables = cur.fetchall()
        if tables:
            for table in tables:
                print(f"Found in Schema: {table[0]}")
        else:
            print("Table 'pb_clients' not found anywhere.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
