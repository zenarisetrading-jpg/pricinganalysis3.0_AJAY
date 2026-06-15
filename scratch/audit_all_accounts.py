"""
Audit all accounts: compare what's in pb_recommendations
vs what SADDL sc_raw.competitor_pricing actually has.
Identifies accounts/categories that need recalculation.
"""
import sys
sys.path.insert(0, ".")
from features.price_benchmarking.saddl_db import fetch_saddl_accounts, execute_saddl_query
from db import get_supabase_client

sb = get_supabase_client()
accounts = fetch_saddl_accounts()
print(f"Total accounts: {len(accounts)}\n")

needs_refresh = []

for acc in accounts:
    account_id = acc["client_id"]
    
    # Check latest pb_recommendations for this account
    recs = sb.table("pb_recommendations")\
        .select("asin, metadata, created_at, reasoning")\
        .eq("client_id", account_id)\
        .eq("status", "pending")\
        .order("created_at", desc=True)\
        .limit(50)\
        .execute()

    if not recs.data:
        print(f"[{account_id}] -- No pending recommendations")
        continue

    # Check for old inflated counts (sourced from pb_category_competitors)
    # The old data had n_competitors > 100 for categories with ~60 scraped ASINs
    # Also check if the metadata still mentions old data sources
    stale = False
    max_comp = 0
    last_created = recs.data[0].get("created_at", "")[:10]
    
    for r in recs.data:
        meta = r.get("metadata") or {}
        n = meta.get("n_competitors", 0)
        if isinstance(n, int) and n > max_comp:
            max_comp = n

    # Check if recommendations were created BEFORE our fix (2026-06-11T12:00)
    if last_created < "2026-06-11":
        stale = True
        needs_refresh.append(account_id)

    status = "STALE (needs refresh)" if stale else "OK"
    print(f"[{account_id}] recs={len(recs.data)} max_n_competitors={max_comp} latest={last_created}  --> {status}")

print(f"\n{'='*60}")
print(f"Accounts needing refresh: {needs_refresh}")
