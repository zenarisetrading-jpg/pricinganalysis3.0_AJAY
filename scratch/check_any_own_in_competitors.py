import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories
sb = get_supabase_client()

products = fetch_account_products_with_categories('oneshot_uae')
own_asins = {p['asin'] for p in products if p.get('asin')}

print(f"Total own active ASINs for oneshot_uae: {len(own_asins)}")

# Fetch all competitor_asin from competitor_products table for oneshot_uae parents
parents = {p['parent_asin'] for p in products if p.get('parent_asin')}

all_competitors = sb.table('competitor_products').select('parent_asin, competitor_asin, competitor_title').in_('parent_asin', list(parents)).execute()

print(f"Total rows in competitor_products for these parents: {len(all_competitors.data)}")

violating_rows = []
for row in all_competitors.data:
    if row['competitor_asin'] in own_asins:
        violating_rows.append(row)

if violating_rows:
    print("WARNING: Found own ASINs in competitor list!")
    for r in violating_rows:
        print(f"  Parent: {r['parent_asin']} | Competitor ASIN: {r['competitor_asin']} | Title: {r['competitor_title']}")
else:
    print("SUCCESS: Zero own ASINs found in competitor lists for all parent ASINs!")
