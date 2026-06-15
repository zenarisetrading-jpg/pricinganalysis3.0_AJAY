import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

p = 'B0DGLGPN1N'
child_asins = ['B0DGLCG5G1', 'B0DGLD7P83', 'B0DGLGPN1N', 'B0DGLHDFPK']
listing_resp = sb.table("pb_client_listings").select("reference_name").in_("asin", [*child_asins, p]).execute()

print("LISTING ROWS FOR B0DGLGPN1N:")
for row in listing_resp.data or []:
    print(f"  Ref: '{row.get('reference_name')}'")
