import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
    CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_mapping 
    ON competitor_products (parent_asin, competitor_asin, marketplace)
    WHERE category_id IS NULL;
    
    CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_category_mapping 
    ON competitor_products (parent_asin, category_id, competitor_asin, marketplace)
    WHERE category_id IS NOT NULL;
"""
try:
    execute_saddl_query(query)
    print("SUCCESS: Created unique indexes")
except Exception as e:
    print(f"FAILED: {e}")
