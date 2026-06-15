import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

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
    print("Deleting duplicates...")
    execute_saddl_query(delete_query)
    print("Duplicates deleted.")
    
    # 2. Apply unique indexes
    index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_mapping 
        ON competitor_products (parent_asin, competitor_asin, marketplace)
        WHERE category_id IS NULL;
        
        CREATE UNIQUE INDEX IF NOT EXISTS unique_competitor_category_mapping 
        ON competitor_products (parent_asin, category_id, competitor_asin, marketplace)
        WHERE category_id IS NOT NULL;
    """
    print("Applying unique indexes...")
    execute_saddl_query(index_query)
    print("SUCCESS: Unique indexes applied.")
except Exception as e:
    print(f"FAILED: {e}")
