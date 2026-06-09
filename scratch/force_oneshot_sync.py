
import os
import sys
from datetime import date
from dotenv import load_dotenv

# Fix path
sys.path.append(os.getcwd())

load_dotenv()

def force_sync():
    from db import get_supabase_client
    from features.price_benchmarking.snapshot_service import calculate_benchmarks_for_client
    
    supabase = get_supabase_client()
    client_id = "oneshot_uae"
    marketplace = "UAE"
    
    print(f"🚀 FORCING SYNC FOR {client_id}...")
    
    # 1. Verify Price Events exist
    events = supabase.table("pb_price_events").select("count", count="exact").eq("marketplace", marketplace).execute().count
    print(f"💰 Found {events} price events in Tier 1.")
    
    if events == 0:
        print("❌ ERROR: No price events found! Apify results didn't save. Checking why...")
        return

    # 2. Trigger Calculation
    print("🧪 Running benchmark calculation logic...")
    try:
        result = calculate_benchmarks_for_client(
            supabase=supabase,
            client_id=client_id,
            marketplace=marketplace,
            snapshot_date=date.today()
        )
        print(f"✅ Calculation Success: {result}")
        
        # 3. Verify Snapshots were saved
        snapshots = supabase.table("pb_client_snapshots_daily").select("count", count="exact").eq("client_id", client_id).execute().count
        print(f"📊 Snapshots now in database: {snapshots}")
        
    except Exception as e:
        print(f"❌ CALCULATION FAILED: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    force_sync()
