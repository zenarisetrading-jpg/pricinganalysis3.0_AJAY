import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()
res = sb.table('pb_recommendations').select('asin, parent_asin, current_price, recommended_price, action, reasoning').eq('client_id', 'oneshot_uae').execute()
print("RECOMMENDATIONS IN DB:")
for r in res.data:
    print(f"ASIN: {r['asin']} | Parent: {r['parent_asin']} | Current: {r['current_price']} | Rec: {r['recommended_price']} | Action: {r['action']}")
    print(f"  Reasoning: {r['reasoning']}")
