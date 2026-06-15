import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import get_supabase_client

sb = get_supabase_client()
recs = sb.table("pb_recommendations").select("*").execute()
print(f"Total recommendations in DB: {len(recs.data)}")
for r in recs.data:
    print(f"Client: {r.get('client_id')} | ASIN: {r.get('asin')} | Status: {r.get('status')} | Price: {r.get('recommended_price')} | Action: {r.get('action')}")
