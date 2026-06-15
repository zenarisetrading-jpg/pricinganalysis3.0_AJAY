import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import get_cached_analysis, fetch_account_products_with_categories, get_supabase_client

sb = get_supabase_client()
products_data = fetch_account_products_with_categories("s2c_uae_test")
print(f"Products count: {len(products_data)}")

seen_parents = set()
for p in products_data:
    parent_asin = p["parent_asin"]
    if parent_asin in seen_parents: continue
    seen_parents.add(parent_asin)
    
    cached = get_cached_analysis(parent_asin, "UAE")
    if cached:
        print(f"Parent: {parent_asin} | Cached Analysis updated_at: {cached.get('updated_at')}")
