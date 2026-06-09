
import os
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_account_products_with_categories

sb = get_supabase_client()
account_id = 'oneshot_uae'

# 1. Fetch all parent ASINs for the account
products = fetch_account_products_with_categories(account_id)
parent_data = {} # parent_asin -> title
for p in products:
    if p['parent_asin'] not in parent_data:
        parent_data[p['parent_asin']] = p['title']

parent_asins = sorted(list(parent_data.keys()))

# 2. Total Competitor Products in DB
total_resp = sb.table('competitor_products').select('*', count='exact').execute()
total_competitors = total_resp.count

# 3. Breakdown per Parent ASIN
report = []
for p_asin in parent_asins:
    resp = sb.table('competitor_products').select('competitor_asin', count='exact').eq('parent_asin', p_asin).execute()
    report.append({
        "parent_asin": p_asin,
        "title": parent_data[p_asin],
        "competitor_count": resp.count
    })

print(f"REPORT_TOTAL:{total_competitors}")
for entry in report:
    print(f"REPORT_ENTRY:{entry['parent_asin']}|{entry['competitor_count']}|{entry['title']}")
