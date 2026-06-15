import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

query = """
    SELECT DISTINCT ON (b.asin)
        b.asin,
        COALESCE(s.parent_asin, b.asin) as parent_asin,
        COALESCE(p.title, b.asin) as title
    FROM sc_raw.bsr_history b
    LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
    LEFT JOIN ads.product_catalog p ON b.asin = p.asin
    WHERE b.account_id = 'oneshot_uae'
      AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history);
"""

rows = execute_saddl_query(query)
print("CLIENT PRODUCTS:")
for r in rows:
    print(f"ASIN: {r[0]} | Parent: {r[1]} | Title: {r[2][:100]}")
