import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

# Check what parent_asin field looks like in recommendations
res = sb.table('pb_recommendations').select('asin,parent_asin,status,current_price,recommended_price,action,reasoning').eq('client_id', 'oneshot_uae').eq('status', 'pending').order('snapshot_date', desc=True).execute()
print(f"Total pending: {len(res.data)}")
for r in res.data:
    print(f"  asin={r['asin']} | parent_asin={r.get('parent_asin')} | action={r['action']}")
