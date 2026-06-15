"""
Force recalculate all accounts using the SADDL-only competitor logic.
Run trigger_background_discovery for every active account.
"""
import sys
sys.path.insert(0, ".")
from features.price_benchmarking.saddl_db import fetch_saddl_accounts
from features.price_benchmarking.discovery_service import trigger_background_discovery

accounts = fetch_saddl_accounts()
print(f"Processing {len(accounts)} accounts...\n")

for acc in accounts:
    account_id = acc["client_id"]
    print(f"{'='*55}")
    print(f"Account: {account_id}")
    try:
        result = trigger_background_discovery(account_id, force=True)
        status = result.get("status", "?")
        n_parents = result.get("parent_asin_count", 0)
        errors = result.get("errors", [])
        print(f"  status={status}  parents={n_parents}  errors={len(errors)}")
        if errors:
            for e in errors[:3]:
                print(f"    ERROR: {e}")
    except Exception as e:
        import traceback
        print(f"  EXCEPTION: {e}")
        traceback.print_exc()

print("\nAll accounts done.")
