import os
import sys
from dotenv import load_dotenv

# Add parent dir to path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import get_supabase_client
from features.price_benchmarking.apify_client import trigger_search_discovery

load_dotenv()

def verify_db():
    supabase = get_supabase_client()
    
    print("Checking accounts table...")
    try:
        accs = supabase.table("accounts").select("*").limit(5).execute()
        print(f"Found {len(accs.data)} accounts.")
        for acc in accs.data:
            print(f" - {acc['account_name']} ({acc['account_id']})")
    except Exception as e:
        print(f"Error checking accounts: {e}")

    print("\nChecking BSR history...")
    try:
        bsr = supabase.table("bsr_history").select("category_name, rank").limit(5).execute()
        print(f"Found {len(bsr.data)} BSR entries.")
    except Exception as e:
        print(f"Error checking bsr_history: {e}")

def verify_apify_trigger():
    print("\nTesting Apify Search Trigger (Dry Run)...")
    # We won't actually trigger it unless APIFY_TOKEN is set and we want to spend money
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("APIFY_TOKEN not set, skipping live trigger test.")
        return
    
    print("Token found. Triggering discovery for 'Kitchen & Dining'...")
    # dataset_id = trigger_search_discovery("Kitchen & Dining", "UAE", max_items=1)
    # print(f"Triggered successfully. Dataset ID: {dataset_id}")
    print("Dry run: trigger_search_discovery('Kitchen & Dining', 'UAE', max_items=1) would be called.")

if __name__ == "__main__":
    verify_db()
    verify_apify_trigger()
