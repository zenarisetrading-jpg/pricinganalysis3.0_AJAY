import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

query = """
    SELECT DISTINCT ON (b.asin)
        b.asin,
        b.category_id,
        b.category_name
    FROM sc_raw.bsr_history b
    WHERE b.account_id = 'oneshot_uae'
      AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
      AND b.asin IN ('B0CZLK598D', 'B0CZLKLJX5', 'B0D39R47CC', 'B0F6NHKSQ1', 'B0FFB2F46C', 'B0FM469PMF', 'B0FMYLRD2X', 'B0FNN5WKDG');
"""

rows = execute_saddl_query(query)
print("CHILD ASIN CATEGORIES IN SADDL:")
for r in rows:
    print(f"ASIN: {r[0]} | Cat ID: {r[1]} | Cat Name: {r[2]}")
