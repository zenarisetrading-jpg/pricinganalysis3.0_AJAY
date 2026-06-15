import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import filter_related_products
sb = get_supabase_client()

cat_sports = '12373047031'
cat_diet = '12373019031'

pool_sports = fetch_competitors_by_category(cat_sports, 'UAE')
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

# For B0DLX3GJNJ
p1_asin = 'B0DLX3GJNJ'
p1_listing = sb.table('pb_client_listings').select('*').eq('asin', p1_asin).execute().data[0]
filtered_p1 = filter_related_products(p1_listing, pool_sports)

# Remove duplicates manually
unique_p1 = []
seen = set()
for c in filtered_p1:
    if c['asin'] not in seen and c['asin'] != p1_asin:
        unique_p1.append(c)
        seen.add(c['asin'])

print(f"B0DLX3GJNJ MATCHED COMPETITORS ({len(unique_p1)}):")
for c in sorted(unique_p1, key=lambda x: x.get('price') or 0):
    print(f"  ASIN: {c['asin']} | Price: {c.get('price')} | Title: {c.get('title')[:80]}")

# For B0FNN5WKDG
p2_asin = 'B0FNN5WKDG'
p2_listing = sb.table('pb_client_listings').select('*').eq('asin', p2_asin).execute().data[0]

merged_pool = []
seen_asins = set()
for item in pool_diet + pool_sports:
    if item['asin'] not in seen_asins:
        merged_pool.append(item)
        seen_asins.add(item['asin'])

filtered_p2 = filter_related_products(p2_listing, merged_pool)
unique_p2 = []
seen = set()
for c in filtered_p2:
    # Exclude child ASINs that are owned by the client!
    # The child ASINs for B0FNN5WKDG are: 'B0CZLK598D', 'B0CZLKLJX5', 'B0D39R47CC', 'B0F6NHKSQ1', 'B0FFB2F46C', 'B0FM469PMF', 'B0FMYLRD2X', 'B0FNN5WKDG'
    own_children = {'B0CZLK598D', 'B0CZLKLJX5', 'B0D39R47CC', 'B0F6NHKSQ1', 'B0FFB2F46C', 'B0FM469PMF', 'B0FMYLRD2X', 'B0FNN5WKDG'}
    if c['asin'] not in seen and c['asin'] not in own_children:
        unique_p2.append(c)
        seen.add(c['asin'])

print(f"\nB0FNN5WKDG MATCHED COMPETITORS ({len(unique_p2)}):")
for c in sorted(unique_p2, key=lambda x: x.get('price') or 0):
    print(f"  ASIN: {c['asin']} | Price: {c.get('price')} | Title: {c.get('title')[:80]}")
