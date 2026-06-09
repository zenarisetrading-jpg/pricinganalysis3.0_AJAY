import os
import sys
from datetime import datetime, timezone

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.price_benchmarking.saddl_db import fetch_saddl_accounts
from features.price_benchmarking.discovery_service import trigger_background_discovery

def run_scheduled_discovery():
    """
    Scheduled job to refresh competitor data for all active accounts.
    """
    print(f"[{datetime.now()}] Starting scheduled competitor discovery...")
    
    # 1. Get all active accounts
    accounts = fetch_saddl_accounts()
    if not accounts:
        print("No accounts found.")
        return
        
    print(f"Found {len(accounts)} accounts to process.")
    
    for acc in accounts:
        account_id = acc.get("account_id")
        if not account_id:
            continue
            
        print(f"Processing account: {account_id}...")
        try:
            # Trigger background discovery
            # This will internally check freshness (24h default)
            status = trigger_background_discovery(account_id)
            print(f"Result for {account_id}: {status['message']}")
        except Exception as e:
            print(f"Error processing account {account_id}: {e}")
            
    print(f"[{datetime.now()}] Scheduled discovery finished.")

if __name__ == "__main__":
    run_scheduled_discovery()
