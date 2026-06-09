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

        # Query to list accounts and look for "aurio"
        query = """
        SELECT account_id, account_name
        FROM public.accounts
        WHERE account_name ILIKE '%aurio%' OR account_id ILIKE '%aurio%'
        """
        cur.execute(query)
        rows = cur.fetchall()
        print("Matching Accounts:")
        for r in rows:
            print(r)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
