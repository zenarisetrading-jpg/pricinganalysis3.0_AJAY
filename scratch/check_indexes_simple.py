import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
    SELECT
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM
        pg_indexes
    WHERE
        tablename = 'competitor_products';
"""
res = execute_saddl_query(query)
for r in res:
    print(r)
