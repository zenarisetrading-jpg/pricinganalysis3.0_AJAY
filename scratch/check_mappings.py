import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_parent_asin_categories, fetch_account_products_with_categories
sb = get_supabase_client()

account_id = 'oneshot_uae'
products = fetch_account_products_with_categories(account_id)
print("PRODUCTS MAPPING:")
parents = {}
for p in products:
    parents.setdefault(p['parent_asin'], []).append(p['asin'])

for p_asin, children in parents.items():
    cats = fetch_parent_asin_categories(account_id, p_asin)
    print(f"Parent: {p_asin} | Children: {children} | Categories: {cats}")
