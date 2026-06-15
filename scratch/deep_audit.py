"""
Deep audit: find any parent ASINs whose n_competitors still looks inflated.
For each account, compare n_competitors in pb_recommendations vs what
SADDL sc_raw.competitor_pricing actually holds for the same category.
"""
import sys
sys.path.insert(0, ".")
from features.price_benchmarking.saddl_db import fetch_saddl_accounts, execute_saddl_query
from db import get_supabase_client

sb = get_supabase_client()
accounts = fetch_saddl_accounts()

for acc in accounts:
    account_id = acc["client_id"]

    recs = sb.table("pb_recommendations")\
        .select("asin, metadata, reasoning, created_at")\
        .eq("client_id", account_id)\
        .eq("status", "pending")\
        .order("created_at", desc=True)\
        .limit(100)\
        .execute()

    if not recs.data:
        continue

    suspects = []
    for r in recs.data:
        meta = r.get("metadata") or {}
        n = meta.get("n_competitors", 0)
        cat_ids = meta.get("category_ids") or []
        if isinstance(n, int) and n > 80:
            suspects.append((r["asin"], n, cat_ids, r["created_at"][:19]))

    if suspects:
        print(f"\n{'='*60}")
        print(f"Account: {account_id} -- HIGH competitor counts:")
        for asin, n, cat_ids, created in suspects:
            print(f"  asin={asin}  n_competitors={n}  cats={cat_ids}  created={created}")
            # Check what's actually in SADDL for those categories
            for cid in cat_ids:
                res = execute_saddl_query("""
                    SELECT COUNT(DISTINCT asin) FROM sc_raw.competitor_pricing
                    WHERE category_id = %s AND price_numeric IS NOT NULL AND price_numeric > 0
                """, (cid,))
                saddl_count = res[0][0] if res else "?"
                match = "OK" if (isinstance(saddl_count, int) and abs(saddl_count - n) <= 5) else "MISMATCH"
                print(f"    cat_id={cid}  SADDL_unique_asins={saddl_count}  [{match}]")

print("\nDone.")
