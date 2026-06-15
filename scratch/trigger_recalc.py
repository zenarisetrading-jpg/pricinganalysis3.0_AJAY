import sys
import os
sys.path.insert(0, '.')

from features.price_benchmarking.discovery_service import trigger_background_discovery

def main():
    account_id = "oneshot_uae"
    print(f"Triggering background discovery/recalculation for account: {account_id}...")
    res = trigger_background_discovery(account_id)
    print("Recalculation results:")
    print(res)

if __name__ == "__main__":
    main()
