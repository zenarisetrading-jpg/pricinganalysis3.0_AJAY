import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_saddl_categories, fetch_account_prices
from features.price_benchmarking.snapshot_service import _resolve_majority_categories

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

client_id = 's2c_test'

# --- Simulate get_overview ---
products = fetch_account_products_with_categories(client_id)
child_to_parent = {p['asin']: p['parent_asin'] for p in products if p.get('asin') and p.get('parent_asin')}

cats = fetch_saddl_categories(client_id)
resolved_products = _resolve_majority_categories(products)
parent_to_resolved_cat = {}
for p in resolved_products:
    pa = p.get('parent_asin')
    cn = p.get('category_name')
    if pa and cn:
        parent_to_resolved_cat[pa.strip()] = cn.strip()

filtered_categories = []
for c in cats:
    c_name_norm = c['category_name'].strip().lower()
    filtered_products = []
    for p in c.get('products', []):
        parent = p.get('asin')
        if parent:
            resolved_cat = parent_to_resolved_cat.get(parent.strip())
            if (resolved_cat and resolved_cat.strip().lower() == c_name_norm) or not resolved_cat:
                filtered_products.append(p)
        else:
            filtered_products.append(p)
    if filtered_products:
        c['products'] = filtered_products
        c['asin_count'] = len(filtered_products)
        filtered_categories.append(c)

parent_asin_count = sum(c['asin_count'] for c in filtered_categories)  # = 16

# Simulate the BSR-filter on snapshot_rows
res = sb.table('pb_client_snapshots_daily').select('asin, parent_asin, snapshot_date').eq('client_id', client_id).order('snapshot_date', desc=True).execute()
raw_snapshots = res.data or []
snapshot_parent_map = {}
for r in raw_snapshots:
    key = child_to_parent.get(r['asin']) or r.get('parent_asin') or r['asin']
    if key not in snapshot_parent_map:
        snapshot_parent_map[key] = r
snapshot_rows = list(snapshot_parent_map.values())

# Apply BSR filter to snapshot_rows (new logic)
bsr_snaps = set()
for _c in filtered_categories:
    for _p in _c.get('products', []):
        _pa = _p.get('asin')
        if _pa:
            bsr_snaps.add(_pa.strip())

filtered_snapshot_rows = [r for r in snapshot_rows if (r.get('parent_asin') or r.get('asin')) in bsr_snaps]

print("=== SIMULATED get_overview RESULT ===")
print("parent_asin_count (Tracked Parent ASINs KPI): " + str(parent_asin_count))
print("snapshot_rows count (product selector items): " + str(len(filtered_snapshot_rows)))

# --- Simulate get_recommendations ---
res2 = sb.table('pb_recommendations').select('asin, parent_asin').eq('client_id', client_id).eq('status', 'pending').execute()
all_recs = res2.data or []

# Simulate _latest_recommendations_by_parent deduplication
parent_map = {}
for r in all_recs:
    key = r.get('parent_asin') or r['asin']
    if key not in parent_map:
        parent_map[key] = r

recs = list(parent_map.values())

# Apply BSR filter (new logic)
filtered_recs = [r for r in recs if (r.get('parent_asin') or r.get('asin')) in bsr_snaps]

print()
print("=== SIMULATED get_recommendations RESULT ===")
print("Recs before BSR filter: " + str(len(recs)))
print("Recs after BSR filter (Pending Recs KPI): " + str(len(filtered_recs)))

print()
print("=== CONSISTENCY CHECK ===")
print("Tracked Parent ASINs KPI: " + str(parent_asin_count))
print("Product selector items:    " + str(len(filtered_snapshot_rows)))
print("Pending Recs KPI:          " + str(len(filtered_recs)))
consistent = (parent_asin_count == len(filtered_snapshot_rows) == len(filtered_recs))
print("All consistent: " + str(consistent))
