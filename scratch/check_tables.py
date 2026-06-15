import sys, os
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

tables = ['pb_client_listings', 'pb_listings', 'competitor_products', 'pb_recommendations', 'pb_client_performance_daily', 'pb_client_snapshots_daily']
for t in tables:
    try:
        res = sb.table(t).select('*').limit(1).execute()
        cols = list(res.data[0].keys()) if res.data else ['(empty)']
        print(f'OK {t}: {cols[:6]}')
    except Exception as e:
        print(f'MISS {t}: {str(e)[:80]}')

# Also check competitor_products columns specifically
print('\n--- competitor_products sample ---')
res = sb.table('competitor_products').select('*').limit(1).execute()
if res.data:
    print(list(res.data[0].keys()))
