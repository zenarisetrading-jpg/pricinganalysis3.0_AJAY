import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category

cat_sports = '12373047031'
cat_diet = '12373019031'

pool_sports = fetch_competitors_by_category(cat_sports, 'UAE')
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

# Get unique ASINs and their titles
unique_sports = {}
for c in pool_sports:
    unique_sports[c['asin']] = c.get('title') or ''

unique_diet = {}
for c in pool_diet:
    unique_diet[c['asin']] = c.get('title') or ''

print(f"UNIQUE SPORTS ASINS IN DB: {len(unique_sports)}")
print("FIRST 20 SPORTS TITLES:")
for asin, title in list(unique_sports.items())[:20]:
    print(f"  {asin}: {title[:80]}")

print(f"\nUNIQUE DIET ASINS IN DB: {len(unique_diet)}")
print("FIRST 20 DIET TITLES:")
for asin, title in list(unique_diet.items())[:20]:
    print(f"  {asin}: {title[:80]}")
