from features.price_benchmarking.saddl_db import execute_saddl_query
query = "SELECT column_name FROM information_schema.columns WHERE table_schema = 'sc_raw' AND table_name = 'sales_traffic'"
print(execute_saddl_query(query, ()))
