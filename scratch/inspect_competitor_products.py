import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_columns():
    url = os.getenv("PRICING_DATABASE_URL")
    if not url:
        print("PRICING_DATABASE_URL not found")
        return
    
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'pb_category_competitors' ORDER BY ordinal_position")
        columns = cur.fetchall()
        print("Columns in pb_category_competitors:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
