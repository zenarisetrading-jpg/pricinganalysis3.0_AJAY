from features.price_benchmarking.saddl_db import execute_saddl_query
query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'ads'"
print(execute_saddl_query(query, ()))
