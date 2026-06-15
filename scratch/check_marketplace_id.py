import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
from features.price_benchmarking.saddl_db import execute_saddl_query

# The previous "ALL UAE" query returned 0 rows for s2c_test categories
# but when we query directly by category_id WITHOUT marketplace_id filter, 
# we DO get data. Let's check what marketplace_id is stored in competitor_pricing.

bsr_cats_with_data = [
    ('28235324031', 'Dish Drying Mats'),
    ('16888907031', 'Disposable Dishes'),
    ('16621133031', 'Handheld Showers'),
    ('26408858031', 'Insulated Bottles'),
    ('22959836031', 'Insulated Cups & Mugs'),
    ('17007680031', 'Sports Water Bottles'),
    ('16888922031', 'Tumblers & Water Glasses'),
    ('85450664031', 'Under Sink Storage'),
]

print("=== marketplace_id stored in competitor_pricing for s2c_test categories ===")
for cat_id, cat_name in bsr_cats_with_data:
    rows = execute_saddl_query(
        "SELECT DISTINCT marketplace_id, COUNT(*) FROM sc_raw.competitor_pricing WHERE category_id = %s GROUP BY marketplace_id",
        (cat_id,)
    )
    for r in rows:
        print(f"  {cat_name}: marketplace_id='{r[0]}' count={r[1]}")

print()
print("=== Expected marketplace_id for UAE: 'A2VIGQ35RCS4UG' ===")
print("=== Checking: was it stored differently? ===")
rows = execute_saddl_query(
    "SELECT DISTINCT marketplace_id FROM sc_raw.competitor_pricing WHERE category_id = '17007680031'",
    ()
)
print(f"Sports Water Bottles marketplace_ids: {[r[0] for r in rows]}")

# Now check what the fetch_all_competitor_pricing_for_account query returns
# It filters by marketplace_id = %s AND category_id IN (SELECT from bsr_history)
# bsr_history has: account_id='s2c_test', category_id=17007680031
# But the fetch_all query was returning 0 rows! Let's see why:

print()
print("=== Debugging fetch_all_competitor_pricing_for_account query ===")
marketplace_id = 'A2VIGQ35RCS4UG'  # UAE

# Check step 1: Does bsr_history have category_ids for s2c_test?
q_bsr = """
    SELECT DISTINCT b.category_id
    FROM sc_raw.bsr_history b
    WHERE b.account_id = 's2c_test'
      AND b.report_date >= (CURRENT_DATE - INTERVAL '90 days')
      AND b.category_id IS NOT NULL
"""
bsr_ids = execute_saddl_query(q_bsr, ())
print(f"BSR category_ids for s2c_test: {[r[0] for r in bsr_ids]}")

# Check step 2: Does competitor_pricing have those category_ids with marketplace_id='A2VIGQ35RCS4UG'?
q_comp = """
    SELECT category_id, marketplace_id, COUNT(*)
    FROM sc_raw.competitor_pricing
    WHERE marketplace_id = 'A2VIGQ35RCS4UG'
      AND category_id IN (
          SELECT DISTINCT b.category_id
          FROM sc_raw.bsr_history b
          WHERE b.account_id = 's2c_test'
            AND b.report_date >= (CURRENT_DATE - INTERVAL '90 days')
            AND b.category_id IS NOT NULL
      )
    GROUP BY category_id, marketplace_id
"""
comp_rows = execute_saddl_query(q_comp, ())
print(f"competitor_pricing rows matching UAE + s2c_test BSR categories: {len(comp_rows)}")
for r in comp_rows:
    print(f"  cat_id={r[0]}, marketplace_id={r[1]}, count={r[2]}")

# The REAL query: without marketplace filter
q_no_mp = """
    SELECT category_id, marketplace_id, COUNT(*)
    FROM sc_raw.competitor_pricing
    WHERE category_id IN (
          SELECT DISTINCT b.category_id
          FROM sc_raw.bsr_history b
          WHERE b.account_id = 's2c_test'
            AND b.report_date >= (CURRENT_DATE - INTERVAL '90 days')
            AND b.category_id IS NOT NULL
      )
    GROUP BY category_id, marketplace_id
"""
all_rows = execute_saddl_query(q_no_mp, ())
print(f"\nWithout marketplace filter: {len(all_rows)} rows")
for r in all_rows:
    print(f"  cat_id={r[0]}, marketplace_id='{r[1]}', count={r[2]}")
