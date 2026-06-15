"""
Targeted diagnostic: Why does B0CGXK9CWT / B0CDJYR8QT show 179/196 competitors?
Focus on HOW the competitor pool is built for those specific ASINs.
"""
import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

TARGET_ASINS = ["B0CGXK9CWT", "B0CDJYR8QT", "B0BCX814PP", "B0CDG L6TZP"]

# Step 1: Find what category IDs these ASINs map to in BSR history
print("=" * 70)
print("STEP 1: What category IDs do our target ASINs map to in bsr_history?")
print("=" * 70)
rows = execute_saddl_query("""
    SELECT b.asin, b.category_id, b.category_name, s.parent_asin, b.report_date
    FROM sc_raw.bsr_history b
    LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
    WHERE (b.asin = ANY(%s) OR s.parent_asin = ANY(%s))
    ORDER BY b.asin, b.report_date DESC
    LIMIT 40;
""", (TARGET_ASINS, TARGET_ASINS))

cat_ids_found = set()
for r in rows:
    print(f"  asin={r[0]}  cat_id={r[1]}  cat_name={r[2]}  parent={r[3]}  date={r[4]}")
    if r[1]:
        cat_ids_found.add(str(r[1]))

# Step 2: Check the competitor_pricing table for those categories
print("\n" + "=" * 70)
print("STEP 2: What's in sc_raw.competitor_pricing for those categories?")
print("(This is the source used to count competitors - NO date filter in code!)")
print("=" * 70)
if cat_ids_found:
    placeholders = ",".join(["%s"] * len(cat_ids_found))
    cat_id_list = list(cat_ids_found)
    rows2 = execute_saddl_query(f"""
        SELECT
            category_id,
            COUNT(*) as total_rows,
            COUNT(DISTINCT asin) as distinct_asins,
            MIN(pulled_at::date) as oldest_date,
            MAX(pulled_at::date) as newest_date
        FROM sc_raw.competitor_pricing
        WHERE category_id IN ({placeholders})
          AND price_numeric IS NOT NULL
          AND price_numeric > 0
        GROUP BY category_id
        ORDER BY distinct_asins DESC;
    """, tuple(cat_id_list))
    for r in rows2:
        print(f"  cat_id={r[0]}")
        print(f"    total_rows    = {r[1]}")
        print(f"    DISTINCT_ASINS= {r[2]}  <-- This is what gets shown as 'competitors'")
        print(f"    oldest_scraped= {r[3]}")
        print(f"    newest_scraped= {r[4]}")

# Step 3: Break down by scrape date to see if data accumulated over time
print("\n" + "=" * 70)
print("STEP 3: competitor_pricing counts per scrape date (accumulation check)")
print("=" * 70)
if cat_ids_found:
    rows3 = execute_saddl_query(f"""
        SELECT
            category_id,
            pulled_at::date as scrape_date,
            COUNT(DISTINCT asin) as distinct_asins
        FROM sc_raw.competitor_pricing
        WHERE category_id IN ({placeholders})
          AND price_numeric IS NOT NULL
          AND price_numeric > 0
        GROUP BY category_id, pulled_at::date
        ORDER BY category_id, scrape_date DESC;
    """, tuple(cat_id_list))
    for r in rows3:
        print(f"  cat_id={r[0]}  date={r[1]}  distinct_asins={r[2]}")

# Step 4: Check the DISTINCT ON query - does the current code deduplicate properly?
print("\n" + "=" * 70)
print("STEP 4: How many UNIQUE asins does the DISTINCT ON query return?")
print("(This is what fetch_all_competitor_pricing_for_account returns)")
print("=" * 70)
if cat_ids_found:
    rows4 = execute_saddl_query(f"""
        SELECT COUNT(*), COUNT(DISTINCT asin) FROM (
            SELECT DISTINCT ON (cp.category_id, cp.asin)
                cp.asin,
                cp.category_id,
                cp.pulled_at
            FROM sc_raw.competitor_pricing cp
            WHERE cp.price_numeric IS NOT NULL
              AND cp.price_numeric > 0
              AND cp.category_id IN ({placeholders})
            ORDER BY cp.category_id, cp.asin, cp.pulled_at DESC
        ) sub;
    """, tuple(cat_id_list))
    for r in rows4:
        print(f"  Result after DISTINCT ON: count={r[0]}, unique_asins={r[1]}")

print("\nDone.")
