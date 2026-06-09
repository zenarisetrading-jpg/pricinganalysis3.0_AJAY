import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
    SELECT
        conname as constraint_name,
        pg_get_constraintdef(c.oid) as constraint_definition
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'public' AND conrelid = 'competitor_products'::regclass;
"""
res = execute_saddl_query(query)
for r in res:
    print(r)
