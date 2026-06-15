"""
Check current state of pb_recommendations for Sports Water Bottle ASINs.
Are there duplicate records? Is the UI reading the old or new ones?
"""
import sys
sys.path.insert(0, ".")
from db import get_supabase_client

sb = get_supabase_client()

TARGET_ASINS = ["B0CGXK9CWT", "B0CDJYR8QT", "B0BCX814PP", "B0CDGL6TZP"]

print("=" * 70)
print("ALL pb_recommendations rows for target ASINs (sorted newest first):")
print("=" * 70)
for asin in TARGET_ASINS:
    rows = sb.table("pb_recommendations")\
        .select("asin, status, reasoning, metadata, created_at, snapshot_date")\
        .eq("asin", asin)\
        .order("created_at", desc=True)\
        .limit(5)\
        .execute()
    print(f"\nASIN: {asin}  ({len(rows.data or [])} total rows)")
    for r in (rows.data or []):
        meta = r.get("metadata") or {}
        n = meta.get("n_competitors", "?")
        reasoning = (r.get("reasoning") or "")[:60]
        print(f"  status={r['status']}  n_competitors={n}  created={r['created_at'][:19]}")
        print(f"  reasoning: {reasoning}")

print("\n" + "=" * 70)
print("CHECKING: Does the get_recommendations endpoint filter by status=pending?")
print("How many PENDING recs exist for s2c_uae_test?")
print("=" * 70)
resp = sb.table("pb_recommendations")\
    .select("asin, status, created_at")\
    .eq("client_id", "s2c_uae_test")\
    .eq("status", "pending")\
    .order("created_at", desc=True)\
    .limit(5)\
    .execute()
print(f"Pending recs for s2c_uae_test: {len(resp.data or [])}")
for r in (resp.data or []):
    print(f"  asin={r['asin']} created={r['created_at'][:19]}")
