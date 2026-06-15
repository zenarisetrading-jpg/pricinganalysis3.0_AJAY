import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import filter_related_products

cat_diet = '12373019031'
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

target = {
    'asin': 'B0DGLGPN1N',
    'parent_asin': 'B0DGLGPN1N',
    'reference_name': 'Electrolyte'
}

filtered = filter_related_products(target, pool_diet)
print(f"Filtered count: {len(filtered)}")
for c in filtered[:15]:
    print(f"  ASIN: {c['asin']} | Score: {c.get('relevance_score'):.2f} | Title: {c.get('title')[:60]}")
