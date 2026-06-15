import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_competitors_by_category, fetch_parent_asin_categories
from features.price_benchmarking.relevance_filter import filter_related_products
sb = get_supabase_client()

account_id = 'oneshot_uae'
cat_sports = '12373047031'
cat_diet = '12373019031'

# Let's inspect B0DLX3GJNJ
p1_asin = 'B0DLX3GJNJ'
p1_listing = sb.table('pb_client_listings').select('*').eq('asin', p1_asin).execute().data[0]
print(f"P1: {p1_asin} | Title: {p1_listing.get('title')} | Ref: {p1_listing.get('reference_name')}")

# Pool for Sports category
pool_sports = fetch_competitors_by_category(cat_sports, 'UAE')
filtered_p1 = filter_related_products(p1_listing, pool_sports)
print(f"Filtered P1 competitors count: {len(filtered_p1)}")
print("Filtered P1 ASINs:", [c['asin'] for c in filtered_p1])

# Let's inspect B0FNN5WKDG
p2_asin = 'B0FNN5WKDG'
p2_listing = sb.table('pb_client_listings').select('*').eq('asin', p2_asin).execute().data[0]
print(f"P2: {p2_asin} | Title: {p2_listing.get('title')} | Ref: {p2_listing.get('reference_name')}")

# Pool for Diet + Sports categories
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')
merged_pool = []
seen_asins = set()
for item in pool_diet + pool_sports:
    if item['asin'] not in seen_asins:
        merged_pool.append(item)
        seen_asins.add(item['asin'])

filtered_p2 = filter_related_products(p2_listing, merged_pool)
print(f"Filtered P2 competitors count: {len(filtered_p2)}")
print("Filtered P2 ASINs:", [c['asin'] for c in filtered_p2])

# Let's check overlap of the filtered sets
print(f"Intersection of filtered sets: {len(set(c['asin'] for c in filtered_p1).intersection(set(c['asin'] for c in filtered_p2)))}")
