"""
Diagnostic: WHY does UI show 179/196 competitors for Sports Water Bottles
when we believe we scraped fewer than 60?

This script checks sc_raw.competitor_pricing (the SADDL table) vs
pb_recommendations (Supabase) to explain the count discrepancy.
"""
import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

# --- Step 1: Find the category IDs for "Sports Water Bottles"
print("=" * 70)
print("STEP 1: Find category IDs for 'Sports Water Bottles' in bsr_history")
print("=" * 70)
rows = execute_saddl_query("""
    SELECT DISTINCT category_id, category_name, COUNT(*) as row_count
    FROM sc_raw.bsr_history
    WHERE LOWER(category_name) LIKE '%water bottle%'
    GROUP BY category_id, category_name
    ORDER BY row_count DESC
    LIMIT 20;
""")
cat_ids = []
for r in rows:
    print(f"  cat_id={r[0]}  name={r[1]}  bsr_rows={r[2]}")
    cat_ids.append(r[0])

# --- Step 2: Count rows in competitor_pricing per category (NO date filter - as current code does)
print("\n" + "=" * 70)
print("STEP 2: competitor_pricing rows per category (NO date filter - current behaviour)")
print("=" * 70)
if cat_ids:
    placeholders = ",".join(["%s"] * len(cat_ids))
    rows2 = execute_saddl_query(f"""
        SELECT category_id,
               COUNT(*) as total_rows,
               COUNT(DISTINCT asin) as distinct_asins,
               MIN(pulled_at) as oldest_scraped,
               MAX(pulled_at) as newest_scraped
        FROM sc_raw.competitor_pricing
        WHERE category_id IN ({placeholders})
          AND price_numeric IS NOT NULL
          AND price_numeric > 0
        GROUP BY category_id
        ORDER BY distinct_asins DESC;
    """, tuple(str(c) for c in cat_ids))
    for r in rows2:
        print(f"  cat_id={r[0]}  total_rows={r[1]}  DISTINCT_ASINS={r[2]}")
        print(f"    oldest_scraped={r[3]}  newest_scraped={r[4]}")

# --- Step 3: Count rows WITH a date filter (last 7 days)
print("\n" + "=" * 70)
print("STEP 3: competitor_pricing rows (WITH date filter: last 7 days)")
print("=" * 70)
if cat_ids:
    rows3 = execute_saddl_query(f"""
        SELECT category_id,
               COUNT(*) as total_rows,
               COUNT(DISTINCT asin) as distinct_asins,
               MIN(pulled_at) as oldest_scraped,
               MAX(pulled_at) as newest_scraped
        FROM sc_raw.competitor_pricing
        WHERE category_id IN ({placeholders})
          AND price_numeric IS NOT NULL
          AND price_numeric > 0
          AND pulled_at >= (CURRENT_DATE - INTERVAL '7 days')
        GROUP BY category_id
        ORDER BY distinct_asins DESC;
    """, tuple(str(c) for c in cat_ids))
    for r in rows3:
        print(f"  cat_id={r[0]}  total_rows={r[1]}  DISTINCT_ASINS_LAST_7D={r[2]}")
        print(f"    oldest={r[3]}  newest={r[4]}")
    if not rows3:
        print("  (no rows in last 7 days)")

# --- Step 4: Count rows per pulled_at date (to see accumulation over time)
print("\n" + "=" * 70)
print("STEP 4: competitor_pricing - count by scraped date (accumulation check)")
print("=" * 70)
if cat_ids:
    rows4 = execute_saddl_query(f"""
        SELECT category_id,
               DATE(pulled_at) as scrape_date,
               COUNT(DISTINCT asin) as distinct_asins
        FROM sc_raw.competitor_pricing
        WHERE category_id IN ({placeholders})
          AND price_numeric IS NOT NULL
          AND price_numeric > 0
        GROUP BY category_id, DATE(pulled_at)
        ORDER BY category_id, scrape_date DESC
        LIMIT 30;
    """, tuple(str(c) for c in cat_ids))
    for r in rows4:
        print(f"  cat_id={r[0]}  date={r[1]}  distinct_asins={r[2]}")

# --- Step 5: Check the pb_recommendations table for these ASINs
print("\n" + "=" * 70)
print("STEP 5: What n_competitors is stored in pb_recommendations metadata?")
print("=" * 70)
try:
    from db import get_supabase_client
    sb = get_supabase_client()
    recs = sb.table("pb_recommendations").select("asin, reasoning, metadata, created_at").eq("status", "pending").order("created_at", desc=True).limit(20).execute()
    for r in (recs.data or []):
        meta = r.get("metadata") or {}
        n = meta.get("n_competitors", "N/A")
        reasoning = (r.get("reasoning") or "")[:80]
        print(f"  asin={r['asin']}  n_competitors={n}  created={r['created_at'][:10]}")
        print(f"    reasoning: {reasoning}")
except Exception as e:
    print(f"  Could not query Supabase: {e}")

print("\nDone.")
