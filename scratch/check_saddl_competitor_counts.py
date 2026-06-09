import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

query = """
    SELECT category_id, category_name, COUNT(DISTINCT asin) as unique_asins
    FROM sc_raw.bsr_history
    WHERE category_id IN ('12373019031', '12373047031')
      AND report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
    GROUP BY category_id, category_name;
"""

rows = execute_saddl_query(query)
print("COMPETITORS IN SADDL BSR HISTORY FOR THE TWO CATEGORIES:")
for r in rows:
    print(f"Cat ID: {r[0]} | Cat Name: {r[1]} | Unique ASINs: {r[2]}")
