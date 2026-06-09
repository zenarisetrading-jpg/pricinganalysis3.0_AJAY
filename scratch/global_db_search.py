import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def global_search(target_string):
    url = os.getenv("SADDL_DATABASE_URL")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Get all text/varchar columns in relevant schemas
        cur.execute("""
            SELECT table_schema, table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema IN ('sc_raw', 'ads', 'public')
              AND data_type IN ('text', 'character varying', 'character')
        """)
        columns = cur.fetchall()
        print(f"Searching {len(columns)} columns...")
        
        for schema, table, col in columns:
            try:
                # We use a simple LIKE check
                query = f"SELECT COUNT(*) FROM {schema}.{table} WHERE {col} = %s"
                cur.execute(query, (target_string,))
                count = cur.fetchone()[0]
                if count > 0:
                    print(f"FOUND in {schema}.{table}.{col}: {count} occurrences")
            except Exception as e:
                # Some tables might be empty or have issues, just skip
                conn.rollback()
                continue
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    global_search("B0CZLKLJX5")
