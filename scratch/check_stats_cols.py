from features.price_benchmarking.saddl_db import execute_saddl_query
query = "SELECT column_name FROM information_schema.columns WHERE table_schema = 'ads' AND table_name = 'product_stats'"
print(execute_saddl_query(query, ()))
