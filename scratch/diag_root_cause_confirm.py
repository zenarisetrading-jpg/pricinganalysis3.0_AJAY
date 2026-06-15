"""
Final confirmation: The 196/179 comes from pb_category_competitors (158 entries)
PLUS pb_price_events (by category_name). Let's confirm the merge logic.
"""
import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import execute_saddl_query

sb = get_supabase_client()
CAT_ID = "17007680031"

# 1. How many ASINs in pb_category_competitors have prices in pb_price_events?
print("=" * 70)
print("CHECK 1: pb_category_competitors (158 ASINs) - how many have prices in pb_price_events?")
print("=" * 70)
cat_comps = sb.table("pb_category_competitors").select("asin").eq("category_id", CAT_ID).eq("is_active", True).execute()
cat_asin_set = {r["asin"] for r in (cat_comps.data or [])}
print(f"  pb_category_competitors has {len(cat_asin_set)} ASINs for this category")

# Get price events for these ASINs
price_events = sb.table("pb_price_events").select("asin, floor_price, buy_box_price, category_name").in_("asin", list(cat_asin_set)).order("created_at", desc=True).execute()
priced_asins = set()
for pe in (price_events.data or []):
    price = pe.get("floor_price") or pe.get("buy_box_price")
    if price and float(price) > 0:
        priced_asins.add(pe["asin"])
print(f"  Of those, {len(priced_asins)} have valid prices in pb_price_events")
print(f"  --> These form the _fetch_category_competitor_price_pool() output")

# 2. The SADDL competitor_pricing has 57 unique ASINs
print("\n" + "=" * 70)
print("CHECK 2: sc_raw.competitor_pricing (SADDL) - unique ASINs")
print("=" * 70)
rows = execute_saddl_query("""
    SELECT COUNT(DISTINCT asin)
    FROM sc_raw.competitor_pricing
    WHERE category_id = '17007680031'
      AND price_numeric IS NOT NULL AND price_numeric > 0
""")
saddl_count = rows[0][0] if rows else 0
print(f"  SADDL competitor_pricing has {saddl_count} distinct ASINs")

# 3. Overlap check
print("\n" + "=" * 70)
print("CHECK 3: Overlap between the two pools")
print("=" * 70)
rows_saddl = execute_saddl_query("""
    SELECT DISTINCT asin FROM sc_raw.competitor_pricing
    WHERE category_id = '17007680031'
      AND price_numeric IS NOT NULL AND price_numeric > 0
""")
saddl_asins = {r[0] for r in rows_saddl}
overlap = priced_asins & saddl_asins
print(f"  Supabase pool (priced from pb_price_events): {len(priced_asins)} ASINs")
print(f"  SADDL pool (sc_raw.competitor_pricing):       {saddl_count} ASINs")
print(f"  Overlap (in both):                            {len(overlap)} ASINs")
print(f"  Union (unique across both sources):           {len(priced_asins | saddl_asins)} ASINs")
print()
print(f"  After _merge_competitor() dedup, max pool size ≈ {len(priced_asins | saddl_asins)}")
print()
print("  NOTE: The relevance_filter THEN removes irrelevant items.")
print("  Remaining after relevance filter = the n shown in the UI (179/196)")

# 4. Summary of why
print("\n" + "=" * 70)
print("ROOT CAUSE SUMMARY")
print("=" * 70)
print(f"""
  You scraped ~57 ASINs into sc_raw.competitor_pricing (SADDL).
  BUT pb_category_competitors (Supabase) has {len(cat_asin_set)} ASINs 
  seeded from Keepa BSR data on 2026-05-19.

  Of those {len(cat_asin_set)}, about {len(priced_asins)} have live prices in pb_price_events.

  fetch_competitors_by_category() MERGES both pools:
    1. _fetch_category_competitor_price_pool():
       → reads pb_category_competitors (158 ASINs)
       → looks up prices in pb_price_events
       → yields ~{len(priced_asins)} priced entries

    2. fetch_competitor_pricing_by_category():
       → reads sc_raw.competitor_pricing
       → yields {saddl_count} entries

  After deduplication: ~{len(priced_asins | saddl_asins)} unique ASINs.

  Then relevance_filter() is applied, which keeps only 'related' products.
  The result = 179 or 196 (depending on which child ASIN is used as reference).

  BOTTOM LINE: The large competitor count is NOT just from your recent scrape.
  It combines Keepa BSR data (158 ASINs, seeded May 19) that already had
  prices in pb_price_events, PLUS the ~57 from your current SADDL scrape.
""")
