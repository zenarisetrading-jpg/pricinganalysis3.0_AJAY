import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

p = 'B0DGLGPN1N'
res_comp = sb.table('competitor_products').select('count', count='exact').eq('parent_asin', p).execute()
res_rec = sb.table('pb_recommendations').select('asin, reasoning').eq('client_id', 'oneshot_uae').execute()

print(f"Kids Hydration Parent: {p}")
print(f"  Competitor count in DB: {res_comp.count}")
for r in res_rec.data:
    if r['asin'] == p:
        print(f"  Reasoning: {r.get('reasoning')}")
