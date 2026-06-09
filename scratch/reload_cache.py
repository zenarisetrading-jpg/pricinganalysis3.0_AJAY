
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("SADDL_DATABASE_URL")
if not db_url:
    print("SADDL_DATABASE_URL not found")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Reload schema cache
    cur.execute("NOTIFY pgrst, 'reload schema'")
    conn.commit()
    print("PostgREST schema cache reload triggered!")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error reloading cache: {e}")
