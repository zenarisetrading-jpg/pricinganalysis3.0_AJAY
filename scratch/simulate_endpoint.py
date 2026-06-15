import sys
sys.path.insert(0, '.')
from features.price_benchmarking.routes import _load_account_parent_map, _latest_recommendations_by_parent
from features.price_benchmarking.discovery_service import get_supabase_client

sb = get_supabase_client()
client_id = "oneshot_uae"

resp = (
    sb.table("pb_recommendations")
    .select("*")
    .eq("client_id", client_id)
    .eq("status", "pending")
    .execute()
)

print(f"Total recommendations fetched from DB for oneshot_uae: {len(resp.data)}")

child_to_parent, parent_asins = _load_account_parent_map(client_id)
print(f"Allowed parent ASINs count: {len(parent_asins)}")
print(f"Allowed parent ASINs: {parent_asins}")

recs = _latest_recommendations_by_parent(resp.data or [], child_to_parent, parent_asins)
print(f"Recommendations returned after filtering: {len(recs)}")
for r in recs:
    print(f"  ASIN: {r.get('asin')} | Title: {r.get('title')[:30]} | Price: {r.get('current_price')} -> {r.get('recommended_price')}")
