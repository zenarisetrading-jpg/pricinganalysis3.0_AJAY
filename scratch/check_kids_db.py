import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

asins = ['B0DGLCG5G1', 'B0DGLD7P83', 'B0DGLGPN1N', 'B0DGLHDFPK']
res = sb.table('pb_client_listings').select('*').in_('asin', asins).execute()

print("CLIENT LISTINGS FOR KIDS HYDRATION:")
for r in res.data:
    print(f"ASIN: {r['asin']} | Client: {r['client_id']} | Ref: '{r.get('reference_name')}' | Active: {r.get('is_active')}")
