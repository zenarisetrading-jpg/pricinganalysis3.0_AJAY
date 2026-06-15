import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

print("1. Total rows in category 17007680031 vs Unique ASINs")
res = execute_saddl_query("""
    SELECT COUNT(*) as total_rows, COUNT(DISTINCT asin) as unique_asins
    FROM sc_raw.competitor_pricing
    WHERE category_id = '17007680031'
      AND price_numeric IS NOT NULL AND price_numeric > 0
""")
print(f"Total rows: {res[0][0]}, Unique ASINs: {res[0][1]}")
