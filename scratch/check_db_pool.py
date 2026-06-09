import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_competitors_by_category, fetch_competitors_for_parent
sb = get_supabase_client()

cat1 = '12373019031' # Diet & Nutrition
cat2 = '12373047031' # Sports Supplements

pool1 = fetch_competitors_by_category(cat1, 'UAE')
pool2 = fetch_competitors_by_category(cat2, 'UAE')

print(f"Competitors in category {cat1} (Diet & Nutrition): {len(pool1)}")
print(f"Competitors in category {cat2} (Sports Supplements): {len(pool2)}")

# Let's see the unique ASINs in each pool
asins1 = {c['asin'] for c in pool1}
asins2 = {c['asin'] for c in pool2}
print(f"Unique ASINs in {cat1}: {len(asins1)}")
print(f"Unique ASINs in {cat2}: {len(asins2)}")
print(f"Intersection of ASINs between the two categories: {len(asins1.intersection(asins2))}")
print(f"Union of ASINs between the two categories: {len(asins1.union(asins2))}")
