import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, execute_saddl_query

own_products = fetch_account_products_with_categories("s2c_test")
own_asins = {p["asin"] for p in own_products if p.get("asin")}

res = execute_saddl_query("""
    SELECT DISTINCT asin
    FROM sc_raw.competitor_pricing
    WHERE category_id = '17007680031'
      AND price_numeric IS NOT NULL AND price_numeric > 0
""")
comp_asins = {r[0] for r in res}

overlap = own_asins & comp_asins

print(f"Total Unique Competitor ASINs in DB: {len(comp_asins)}")
print(f"Account's Own ASINs: {len(own_asins)}")
print(f"Overlap (Own ASINs in competitor DB): {len(overlap)}")
print(f"ASINs in overlap: {overlap}")
