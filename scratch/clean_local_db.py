import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
PRICING_DATABASE_URL = os.getenv("PRICING_DATABASE_URL")

def clean_local_db():
    conn = psycopg2.connect(PRICING_DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Delete duplicates, keeping the latest one by ID
    delete_query = """
        DELETE FROM competitor_products a USING competitor_products b
        WHERE a.id < b.id 
        AND a.parent_asin = b.parent_asin 
        AND a.competitor_asin = b.competitor_asin 
        AND a.marketplace = b.marketplace
        AND (a.category_id = b.category_id OR (a.category_id IS NULL AND b.category_id IS NULL));
    """

    try:
        print("Deleting duplicates from LOCAL database...")
        cur.execute(delete_query)
        print(f"Deleted {cur.rowcount} duplicates.")
        
        # 2. Apply unique indexes to prevent future duplicates
        index_queries = [
            """
            CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_mapping 
            ON competitor_products (parent_asin, competitor_asin, marketplace)
            WHERE category_id IS NULL;
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_category_mapping 
            ON competitor_products (parent_asin, category_id, competitor_asin, marketplace)
            WHERE category_id IS NOT NULL;
            """
        ]
        
        for q in index_queries:
            print("Applying unique index...")
            cur.execute(q)
            
        print("SUCCESS: Local database cleaned and secured with unique indexes.")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    clean_local_db()
