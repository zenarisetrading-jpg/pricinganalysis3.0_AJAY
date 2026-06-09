from db import get_supabase_client
sb = get_supabase_client()
res = sb.table('pb_recommendations').select('*').eq('client_id', 'oneshot_uae').eq('parent_asin', 'B0FNN5WKDG').execute()
print(f"Found {len(res.data)} recommendations for parent B0FNN5WKDG")
for r in res.data:
    print(f"ASIN: {r['asin']} | Created: {r['created_at']} | Reasoning: {r['reasoning'][:50]}...")
