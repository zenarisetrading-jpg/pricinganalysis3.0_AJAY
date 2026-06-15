import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_saddl_categories
from features.price_benchmarking.snapshot_service import _resolve_majority_categories

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

client_id = 's2c_test'

# === 1. What "Tracked Parent ASINs" KPI sources from ===
products = fetch_account_products_with_categories(client_id)
child_to_parent = {p['asin']: p['parent_asin'] for p in products if p.get('asin') and p.get('parent_asin')}

cats = fetch_saddl_categories(client_id)
resolved = _resolve_majority_categories(products)
parent_to_resolved_cat = {}
for p in resolved:
    parent = p.get('parent_asin')
    cat_name = p.get('category_name')
    if parent and cat_name:
        parent_to_resolved_cat[parent.strip()] = cat_name.strip()

# This is what the overview endpoint calculates as parent_asin_count
filtered_categories = []
for c in cats:
    c_name_norm = c['category_name'].strip().lower()
    filtered_products = []
    for p in c.get('products', []):
        parent = p.get('asin')
        if parent:
            resolved_cat = parent_to_resolved_cat.get(parent.strip())
            if resolved_cat and resolved_cat.strip().lower() == c_name_norm:
                filtered_products.append(p)
            elif not resolved_cat:
                filtered_products.append(p)
        else:
            filtered_products.append(p)
    if filtered_products:
        c['products'] = filtered_products
        c['asin_count'] = len(filtered_products)
        filtered_categories.append(c)

parent_asin_count_from_cats = sum(c['asin_count'] for c in filtered_categories)
bsr_parent_asins = set()
for c in filtered_categories:
    for p in c.get('products', []):
        bsr_parent_asins.add(p['asin'])

print("=== SOURCE 1: 'Tracked Parent ASINs' KPI ===")
print("Calculated from: filtered BSR categories (parent_asin_count in overview API)")
print("Value: " + str(parent_asin_count_from_cats))
print("Parent ASINs included: " + str(sorted(bsr_parent_asins)))

# === 2. What "Pending Recs" KPI sources from ===
res2 = sb.table('pb_recommendations').select('asin, parent_asin').eq('client_id', client_id).eq('status', 'pending').execute()
all_recs = res2.data or []

# Deduplicate by parent_asin (same logic as frontend renderRecommendations)
parent_map = {}
for r in all_recs:
    key = r.get('parent_asin') or r['asin']
    if key not in parent_map:
        parent_map[key] = r
    else:
        existing = parent_map[key]
        is_canonical = r.get('asin') == r.get('parent_asin')
        existing_canonical = existing.get('asin') == existing.get('parent_asin')
        if is_canonical and not existing_canonical:
            parent_map[key] = r

rec_parent_asins = set(parent_map.keys())
print()
print("=== SOURCE 2: 'Pending Recs' KPI ===")
print("Calculated from: deduplicated pb_recommendations by parent_asin")
print("Value: " + str(len(rec_parent_asins)))
print("Parent ASINs included: " + str(sorted(rec_parent_asins)))

# === 3. The DIFF ===
print()
print("=== MISMATCH ANALYSIS ===")
extra_in_recs = rec_parent_asins - bsr_parent_asins
missing_from_recs = bsr_parent_asins - rec_parent_asins
print("In recs but NOT in BSR categories (" + str(len(extra_in_recs)) + "): " + str(sorted(extra_in_recs)))
print("In BSR categories but NOT in recs (" + str(len(missing_from_recs)) + "): " + str(sorted(missing_from_recs)))

# Show resolved categories for extra recs
print()
print("Resolved categories for extra parent ASINs:")
for pa in sorted(extra_in_recs):
    cat = parent_to_resolved_cat.get(pa, 'NOT IN SADDL')
    print("  " + pa + " -> " + str(cat))

# === 4. What snapshot_rows gives (the actual overview API rows) ===
res3 = sb.table('pb_client_snapshots_daily').select('asin, parent_asin, snapshot_date').eq('client_id', client_id).order('snapshot_date', desc=True).execute()
snap_rows = res3.data or []
snap_parent_map = {}
for r in snap_rows:
    key = child_to_parent.get(r['asin']) or r.get('parent_asin') or r['asin']
    if key not in snap_parent_map:
        snap_parent_map[key] = r
print()
print("=== SOURCE 3: Actual snapshot rows (uniqueRows in frontend) ===")
print("Value: " + str(len(snap_parent_map)))
print("These are what appear in the product selector dropdown")
