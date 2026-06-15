"""
Re-run analysis for ALL active accounts using the updated competitor fetch logic
(SADDL sc_raw.competitor_pricing ONLY — Supabase pool excluded).

This replaces the stored pb_recommendations with the corrected competitor counts.
"""
import sys
sys.path.insert(0, ".")

from features.price_benchmarking.saddl_db import fetch_saddl_accounts
from features.price_benchmarking.discovery_service import trigger_background_discovery

accounts = fetch_saddl_accounts()
print(f"Found {len(accounts)} accounts to process.\n")

for acc in accounts:
    account_id = acc["client_id"]
    print("=" * 60)
    print(f"Processing account: {account_id}")
    print("=" * 60)
    try:
        result = trigger_background_discovery(account_id, force=False)
        print(f"  status          : {result.get('status')}")
        print(f"  parent_asins    : {result.get('parent_asin_count', 0)}")
        print(f"  errors          : {result.get('errors', [])}")
    except Exception as e:
        import traceback
        print(f"  ERROR for {account_id}:")
        traceback.print_exc()
    print()

print("All accounts processed.")
