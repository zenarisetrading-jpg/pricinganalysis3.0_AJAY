import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("PRICING_DATABASE_URL")
    if not db_url:
        print("PRICING_DATABASE_URL not found")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        query = """
        SELECT table_schema, table_name 
        FROM information_schema.columns 
        WHERE column_name = 'parent_asin'
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        print("Tables containing 'parent_asin':")
        for r in rows:
            print(f"- {r[0]}.{r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
