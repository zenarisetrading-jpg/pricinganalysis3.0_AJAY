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

        for acct in ['aurio_uae', 'uae_aurio']:
            cur.execute("SELECT COUNT(*) FROM sc_raw.bsr_history WHERE account_id = %s", (acct,))
            bsr_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM sc_raw.sales_traffic WHERE account_id = %s", (acct,))
            traffic_count = cur.fetchone()[0]
            
            print(f"Account: {acct} | BSR rows: {bsr_count} | Sales Traffic rows: {traffic_count}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
