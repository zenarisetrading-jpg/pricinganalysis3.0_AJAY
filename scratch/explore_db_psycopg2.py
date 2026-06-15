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
        
        print("--- Listing Tables in public schema ---")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        for table in tables:
            print(f"Table: {table[0]}")
            
        print("\n--- Checking columns of public.accounts (if it exists) ---")
        try:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'accounts' AND table_schema = 'public'
            """)
            columns = cur.fetchall()
            if columns:
                for col in columns:
                    print(f"Column: {col[0]} ({col[1]})")
                
                print("\n--- Querying public.accounts ---")
                cur.execute("SELECT * FROM public.accounts")
                rows = cur.fetchall()
                print(f"Rows: {rows}")
            else:
                print("Table 'accounts' does not exist in 'public' schema.")
        except Exception as e:
            print(f"Error checking accounts: {e}")
            conn.rollback()

        print("\n--- Checking columns of public.pb_clients ---")
        try:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'pb_clients' AND table_schema = 'public'
            """)
            columns = cur.fetchall()
            for col in columns:
                print(f"Column: {col[0]} ({col[1]})")
                
            print("\n--- Querying public.pb_clients ---")
            cur.execute("SELECT * FROM public.pb_clients")
            rows = cur.fetchall()
            print(f"Rows: {rows}")
        except Exception as e:
            print(f"Error checking pb_clients: {e}")
            conn.rollback()

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
