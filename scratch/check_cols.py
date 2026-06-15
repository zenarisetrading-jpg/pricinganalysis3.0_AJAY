import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query
res = execute_saddl_query("SELECT column_name FROM information_schema.columns WHERE table_name = 'competitor_products'")
for r in res:
    print(r)
