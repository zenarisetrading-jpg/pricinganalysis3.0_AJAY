import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, execute_saddl_query

products = fetch_account_products_with_categories("s2c_uae_test")
print(f"Total products for s2c_uae_test: {len(products)}")

unique_categories = set()
for p in products:
    cat_id = p.get("category_id")
    if cat_id:
        unique_categories.add(cat_id)

print(f"Unique categories: {unique_categories}")

for cat_id in sorted(list(unique_categories)):
    # Query competitor_pricing row count for this category
    query = "SELECT COUNT(*) FROM sc_raw.competitor_pricing WHERE category_id = %s"
    count = execute_saddl_query(query, (cat_id,))[0][0]
    print(f"  Category ID: {cat_id} | Competitor pricing row count: {count}")
