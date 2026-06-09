from features.price_benchmarking.saddl_db import execute_saddl_query
query = "SELECT asin, units_ordered, sessions, acos_pct, report_date FROM sc_raw.bsr_history WHERE account_id = 'oneshot_uae' LIMIT 10"
print(execute_saddl_query(query, ()))
