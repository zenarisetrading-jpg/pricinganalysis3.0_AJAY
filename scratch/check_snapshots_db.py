import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import get_supabase_client

sb = get_supabase_client()
snaps = sb.table("pb_client_snapshots_daily").select("*").eq("client_id", "oneshot_uae").execute()
print(f"Total snapshots in DB: {len(snaps.data)}")
for s in snaps.data:
    print(f"Client: {s.get('client_id')} | ASIN: {s.get('asin')} | Date: {s.get('snapshot_date')} | Your Price: {s.get('your_price')} | Competitors: {s.get('n_competitors')}")
