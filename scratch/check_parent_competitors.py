import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_competitors_for_parent
from features.price_benchmarking.relevance_filter import filter_related_products
sb = get_supabase_client()

parents = ['B0DLX3GJNJ', 'B0DLX3Y8JN', 'B0DLX4FKPT', 'B0DLXPQZCJ', 'B0FM43BSB2', 'B0FM45GBTY', 'B0FNN5WKDG']

print("IF WE QUERY BY parent_asin SPECIFICALLY:")
for p in parents:
    # Fetch listing for keyword filtering
    listing_resp = sb.table('pb_client_listings').select('*').eq('asin', p).execute()
    listing = listing_resp.data[0] if listing_resp.data else {'asin': p, 'reference_name': 'Electrolyte'}
    
    pool = fetch_competitors_for_parent(p, 'UAE')
    unique_pool = []
    seen = set()
    for item in pool:
        if item['asin'] not in seen:
            unique_pool.append(item)
            seen.add(item['asin'])
            
    filtered = filter_related_products(listing, unique_pool)
    print(f"Parent ASIN: {p} | Unique Pool: {len(unique_pool)} | Filtered (Keyword): {len(filtered)}")
