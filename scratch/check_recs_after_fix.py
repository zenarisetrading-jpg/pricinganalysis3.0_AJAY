import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

# Fetch recommendations for B0DLX3GJNJ and B0FNN5WKDG from db
parents = ['B0DLX3GJNJ', 'B0FNN5WKDG']

res = sb.table('pb_recommendations').select('asin, strategy, reasoning').eq('client_id', 'oneshot_uae').execute()

# Fetch SADDL mapping to group by parent
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories
products = fetch_account_products_with_categories('oneshot_uae')
parent_map = {p['asin']: p['parent_asin'] for p in products}

print("RECOMMENDATIONS IN DB AFTER FIX:")
for r in res.data:
    asin = r['asin']
    parent = parent_map.get(asin, asin)
    if parent in parents:
        print(f"Parent: {parent} | ASIN: {asin} | Reasoning: {r.get('reasoning')}")
