from db import get_supabase_client
sb = get_supabase_client()
res = sb.table('pb_recommendations').select('asin,parent_asin,current_price,recommended_price,reasoning').eq('client_id','oneshot_uae').execute()
print(f"Total records: {len(res.data)}")
for r in res.data:
    print(f"  {r['asin']} | Current: {r['current_price']} | Target: {r['recommended_price']}")
