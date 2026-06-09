
import os
import sys
from dotenv import load_dotenv

# Fix path
sys.path.append(os.getcwd())

load_dotenv()

def check_stats():
    from db import get_supabase_client
    supabase = get_supabase_client()
    
    url = os.getenv("SUPABASE_URL")
    print(f"📡 Database: {url}")
    print("-" * 50)
    
    # 1. Check Clients
    clients = supabase.table("pb_clients").select("client_id").execute().data
    print(f"✅ Clients found: {[c['client_id'] for c in clients]}")
    
    # 2. Check Listings
    listings_count = supabase.table("pb_client_listings").select("count", count="exact").eq("client_id", "oneshot_uae").execute().count
    print(f"📦 Listings for OneShot: {listings_count}")
    
    # 3. Check Price Events
    events_count = supabase.table("pb_price_events").select("count", count="exact").eq("marketplace", "UAE").execute().count
    print(f"💰 Price Events (UAE): {events_count}")
    
    # 4. Check Snapshots
    snapshots_count = supabase.table("pb_client_snapshots_daily").select("count", count="exact").eq("client_id", "oneshot_uae").execute().count
    print(f"📊 Analysis Snapshots: {snapshots_count}")
    print("-" * 50)
    
    if events_count > 0 and snapshots_count == 0:
        print("💡 TIP: You have price data, but the dashboard analysis hasn't run yet.")
        print("Try running: .\\.venv\\Scripts\\python.exe d:\\pricing_analysis\\scratch\\onboard_oneshot_full.py")

if __name__ == "__main__":
    check_stats()
