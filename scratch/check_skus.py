import sys
import os
sys.path.append(os.getcwd())
from db import get_supabase_client

def check():
    s = get_supabase_client()
    client_id = "oneshot_uae"
    
    # Check SKUs
    skus = s.table("pb_benchmarking_skus").select("*").eq("client_id", client_id).execute()
    print(f"🔍 Total SKUs for {client_id}: {len(skus.data)}")
    if len(skus.data) > 0:
        print(f"Sample ASIN: {skus.data[0]['asin']}")
        
    # Check Price Events for today
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    events = s.table("pb_price_events").select("count", count="exact").eq("marketplace", "UAE").gte("created_at", today).execute()
    print(f"💰 Price Events for today ({today}): {events.count}")

if __name__ == "__main__":
    check()
