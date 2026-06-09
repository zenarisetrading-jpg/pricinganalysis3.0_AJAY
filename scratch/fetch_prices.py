from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
    SELECT child_asin, SUM(ordered_revenue) / SUM(units_ordered) as avg_price
    FROM sc_raw.sales_traffic
    WHERE account_id = 'oneshot_uae' AND units_ordered > 0
    GROUP BY child_asin
"""
res = execute_saddl_query(query)
for r in res:
    print(f"ASIN: {r[0]} | Price: {r[1]}")
