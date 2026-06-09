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
        
        print("--- Checking sc_raw.bsr_history ---")
        cur.execute("SELECT count(*) FROM sc_raw.bsr_history")
        count = cur.fetchone()[0]
        print(f"Total rows in bsr_history: {count}")
        
        if count > 0:
            cur.execute("SELECT * FROM sc_raw.bsr_history LIMIT 5")
            rows = cur.fetchall()
            for row in rows:
                print(row)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
