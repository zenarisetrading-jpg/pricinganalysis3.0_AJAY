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
        
        print("--- Accounts in SADDL DB ---")
        cur.execute("SELECT * FROM amazon_accounts LIMIT 1")
        colnames = [desc[0] for desc in cur.description]
        print(f"Columns: {colnames}")
        
        cur.execute("SELECT id, display_name, marketplace FROM amazon_accounts")
        accounts = cur.fetchall()
        for acc in accounts:
            print(f"ID: {acc[0]} | Name: {acc[1]} | Marketplace: {acc[2]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
