import psycopg2
import sys
import os
import dotenv

# Load .env
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def test_conn():
    url = os.environ.get("PRICING_DATABASE_URL")
    if not url:
        print("❌ PRICING_DATABASE_URL not set in .env")
        return
    print(f"Testing connection to: {url.split('@')[1] if '@' in url else url}")
    try:
        conn = psycopg2.connect(url)
        print("✅ Connection successful!")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"Server version: {cur.fetchone()}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_conn()
