import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import filter_related_products
sb = get_supabase_client()

cat_diet = '12373019031'
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

target = {
    'asin': 'B0DGLGPN1N',
    'parent_asin': 'B0DGLGPN1N',
    'reference_name': 'Electrolyte'
}

filtered = filter_related_products(target, pool_diet)
print(f"Direct filter pool size: {len(pool_diet)}")
print(f"Filtered size with 'Electrolyte': {len(filtered)}")

# Check without reference name
target_none = {
    'asin': 'B0DGLGPN1N',
    'parent_asin': 'B0DGLGPN1N',
    'reference_name': None
}
filtered_none = filter_related_products(target_none, pool_diet)
print(f"Filtered size with None: {len(filtered_none)}")
