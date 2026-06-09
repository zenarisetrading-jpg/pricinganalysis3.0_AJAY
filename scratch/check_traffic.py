from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
    SELECT child_asin, units_ordered, sessions, report_date 
    FROM sc_raw.sales_traffic 
    WHERE account_id = 'oneshot_uae' AND report_date = '2026-05-14'
    LIMIT 10
"""
res = execute_saddl_query(query)
for r in res:
    print(r)
