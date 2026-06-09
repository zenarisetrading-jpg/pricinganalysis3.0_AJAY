
import requests
import os
import sys
from dotenv import load_dotenv

# Fix Python Path
sys.path.append(os.getcwd())

load_dotenv()

API_BASE = "http://127.0.0.1:8000/api/v1/benchmarking"
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "saddl_secret_token_123")
CLIENT_ID = "oneshot_uae"
MARKETPLACE = "UAE"

def clean_and_refresh():
    from db import get_supabase_client
    supabase = get_supabase_client()
    
    print(f"🗑️  Cleaning all existing data for {CLIENT_ID}...")
    
    try:
        # Delete old snapshots
        supabase.table("pb_client_snapshots_daily").delete().eq("client_id", CLIENT_ID).execute()
        # Delete old price events
        supabase.table("pb_price_events").delete().eq("marketplace", MARKETPLACE).execute()
        # Delete old alerts
        supabase.table("pb_alerts").delete().eq("client_id", CLIENT_ID).execute()
        
        print("✅ Database cleaned. All old analysis has been removed.")

        # Trigger new scrape
        print(f"🚀 Triggering a FRESH Apify scrape for all tracked products...")
        headers = {"X-Internal-Token": INTERNAL_TOKEN, "Content-Type": "application/json"}
        
        # Get active ASINs from our local listings
        listings_resp = supabase.table("pb_client_listings").select("asin").eq("client_id", CLIENT_ID).execute()
        asins = [r["asin"] for r in (listings_resp.data or [])]
        
        if not asins:
            print("⚠️ No products found in listings. Please run onboard_oneshot_full.py first.")
            return

        resp = requests.post(f"{API_BASE}/trigger-scrape", headers=headers, params={"marketplace": MARKETPLACE}, json=asins)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"\n✨ SUCCESS! Fresh Apify analysis triggered for {len(asins)} products.")
            print(f"New Dataset ID: {result.get('dataset_id')}")
            print(f"Wait 2 minutes, then run fetch_apify_results.py with this new ID.")
        else:
            print(f"❌ Failed to trigger scrape: {resp.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    clean_and_refresh()
