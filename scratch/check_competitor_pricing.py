import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
import os
from features.price_benchmarking.saddl_db import execute_saddl_query, fetch_account_products_with_categories

account_id = 's2c_test'
marketplace_id = 'A2VIGQ35RCS4UG'  # UAE

# Step 1: What category_ids belong to s2c_test via bsr_history?
q1 = """
    SELECT DISTINCT b.category_id, b.category_name, COUNT(*) as bsr_rows
    FROM sc_raw.bsr_history b
    WHERE b.account_id = %s
      AND b.report_date >= (CURRENT_DATE - INTERVAL '90 days')
      AND b.category_id IS NOT NULL
    GROUP BY b.category_id, b.category_name
    ORDER BY b.category_name
"""
bsr_cats = execute_saddl_query(q1, (account_id,))
print("=== BSR CATEGORIES FOR s2c_test (last 90 days) ===")
bsr_cat_ids = []
for r in bsr_cats:
    print(f"  cat_id={r[0]} | name={r[1]} | bsr_rows={r[2]}")
    bsr_cat_ids.append(str(r[0]))
print(f"Total: {len(bsr_cats)} categories\n")

# Step 2: What's in sc_raw.competitor_pricing for UAE, per category?
q2 = """
    SELECT category_id, COUNT(*) as rows, MIN(pulled_at)::date, MAX(pulled_at)::date
    FROM sc_raw.competitor_pricing
    WHERE marketplace_id = %s
    GROUP BY category_id
    ORDER BY MAX(pulled_at) DESC
    LIMIT 50
"""
comp_cats = execute_saddl_query(q2, (marketplace_id,))
print("=== sc_raw.competitor_pricing (UAE, all categories with data) ===")
comp_cat_ids = set()
for r in comp_cats:
    match = "MATCHES s2c_test" if str(r[0]) in bsr_cat_ids else "no match"
    print(f"  cat_id={r[0]} | rows={r[1]} | from={r[2]} to={r[3]} | {match}")
    comp_cat_ids.add(str(r[0]))
print(f"Total categories with competitor data: {len(comp_cats)}\n")

# Step 3: Coverage check
print("=== COVERAGE: s2c_test BSR categories vs competitor_pricing ===")
have_data = []
missing = []
for r in bsr_cats:
    cat_id = str(r[0])
    cat_name = r[1]
    if cat_id in comp_cat_ids:
        q3 = "SELECT COUNT(*), MAX(pulled_at)::date FROM sc_raw.competitor_pricing WHERE category_id = %s AND marketplace_id = %s"
        cnt = execute_saddl_query(q3, (r[0], marketplace_id))
        count = cnt[0][0] if cnt else 0
        last_scraped = cnt[0][1] if cnt else 'unknown'
        have_data.append((cat_id, cat_name, count))
        print(f"  [HAS DATA] {cat_name} (id={cat_id}) -> {count} rows, last scraped={last_scraped}")
    else:
        missing.append((cat_id, cat_name))
        print(f"  [MISSING]  {cat_name} (id={cat_id}) -> NO DATA in sc_raw.competitor_pricing")

print(f"\nHave data: {len(have_data)}/{len(bsr_cats)} categories")
print(f"Missing:   {len(missing)}/{len(bsr_cats)} categories")

if missing:
    print("\nMissing category IDs (need scraping):")
    for cat_id, cat_name in missing:
        print(f"  {cat_name}: node={cat_id}")

# Step 4: Parent ASIN -> competitor data mapping
print("\n=== PARENT ASIN -> CATEGORY -> COMPETITOR DATA STATUS ===")
products = fetch_account_products_with_categories(account_id)
parent_to_cat = {}
for p in products:
    pa = p.get('parent_asin') or p.get('asin')
    cat_id = str(p.get('category_id') or '')
    cat_name = p.get('category_name', '')
    if pa and cat_id and pa not in parent_to_cat:
        parent_to_cat[pa] = {'cat_id': cat_id, 'cat_name': cat_name}

have_data_ids = {d[0] for d in have_data}
for pa, info in sorted(parent_to_cat.items()):
    status = "HAS DATA" if info['cat_id'] in have_data_ids else "NO COMPETITOR DATA"
    print(f"  [{status}] {pa} -> {info['cat_name']} (cat_id={info['cat_id']})")
