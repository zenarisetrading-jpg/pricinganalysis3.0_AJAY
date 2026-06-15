import os, sys
from dotenv import load_dotenv
load_dotenv()

from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_saddl_categories
from features.price_benchmarking.snapshot_service import _resolve_majority_categories
from supabase import create_client

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

client_id = 's2c_test'
print('=== SADDL Products ===')
products = fetch_account_products_with_categories(client_id)
child_to_parent = {p['asin']: p['parent_asin'] for p in products if p.get('asin') and p.get('parent_asin')}
parent_asins = set(child_to_parent.values())
print(f'Total child ASINs: {len(products)}')
print(f'Total unique parent ASINs: {len(parent_asins)}')
print()

print('=== SADDL Categories (raw) ===')
cats = fetch_saddl_categories(client_id)
print(f'Total categories: {len(cats)}')
for c in cats:
    print(f'  Category: {c["category_name"]} -> {c["asin_count"]} parent ASINs')
    for p in c.get('products', []):
        print(f'    - {p["asin"]}')
print()

print('=== After _resolve_majority_categories ===')
resolved = _resolve_majority_categories(products)
parent_to_resolved_cat = {}
for p in resolved:
    parent = p.get('parent_asin')
    cat_name = p.get('category_name')
    if parent and cat_name:
        parent_to_resolved_cat[parent.strip()] = cat_name.strip()

print(f'Unique parent->resolved category mappings: {len(parent_to_resolved_cat)}')
for pa, cat in sorted(parent_to_resolved_cat.items()):
    print(f'  {pa} -> {cat}')
print()

print('=== Filtered categories (what get_account_bsr_categories returns) ===')
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

print(f'Total filtered categories: {len(filtered_categories)}')
total_parent_asins = 0
for c in filtered_categories:
    print(f'  Category: {c["category_name"]} -> {c["asin_count"]} parent ASINs')
    for p in c.get('products', []):
        print(f'    - {p["asin"]}')
    total_parent_asins += c['asin_count']
print(f'Total parent ASINs in filtered categories: {total_parent_asins}')
print()

print('=== Snapshots in Supabase ===')
res = sb.table('pb_client_snapshots_daily').select('asin, parent_asin, snapshot_date').eq('client_id', client_id).order('snapshot_date', desc=True).execute()
snapshot_rows = res.data or []
snapshot_parent_map = {}
for r in snapshot_rows:
    key = child_to_parent.get(r['asin']) or r.get('parent_asin') or r['asin']
    if key not in snapshot_parent_map:
        snapshot_parent_map[key] = r
print(f'Total snapshot rows: {len(snapshot_rows)}')
print(f'Unique parent ASINs in snapshots: {len(snapshot_parent_map)}')
for pa in sorted(snapshot_parent_map.keys()):
    print(f'  - {pa} (date: {snapshot_parent_map[pa].get("snapshot_date")})')
print()

print('=== Parent ASINs in SADDL but NOT in snapshots ===')
missing = parent_asins - set(snapshot_parent_map.keys())
print(f'Missing: {len(missing)}')
for pa in sorted(missing):
    print(f'  - {pa}')
