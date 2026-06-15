import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
import os, json
from supabase import create_client
from features.price_benchmarking.saddl_db import (
    fetch_account_prices, fetch_account_products_with_categories, fetch_saddl_categories
)
from features.price_benchmarking.snapshot_service import _resolve_majority_categories
from features.price_benchmarking.routes import _load_account_parent_map, _latest_recommendations_by_parent
from typing import Dict

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)
client_id = 's2c_test'

# Simulate the full get_recommendations flow
child_to_parent, parent_asins = _load_account_parent_map(client_id)
resp = sb.table('pb_recommendations').select('*').eq('client_id', client_id).eq('status', 'pending').order('created_at', desc=True).execute()

saddl_products = fetch_account_products_with_categories(client_id)
cats = fetch_saddl_categories(client_id)
resolved_products = _resolve_majority_categories(saddl_products)

_parent_to_resolved_cat: Dict[str, str] = {}
for _p in resolved_products:
    _pa = _p.get('parent_asin')
    _cn = _p.get('category_name')
    if _pa and _cn:
        _parent_to_resolved_cat[_pa.strip()] = _cn.strip()

_bsr_parent_asins = set()
for _c in cats:
    _c_norm = _c['category_name'].strip().lower()
    for _p in _c.get('products', []):
        _pa = _p.get('asin')
        if _pa:
            _resolved = _parent_to_resolved_cat.get(_pa.strip())
            if (_resolved and _resolved.strip().lower() == _c_norm) or not _resolved:
                _bsr_parent_asins.add(_pa.strip())

if _bsr_parent_asins:
    parent_asins = _bsr_parent_asins

recs = _latest_recommendations_by_parent(resp.data or [], child_to_parent, parent_asins)
filtered_recs = [r for r in recs if (r.get('parent_asin') or r.get('asin')) in _bsr_parent_asins]

# Add category_name
for r in filtered_recs:
    pa = r.get('parent_asin') or r.get('asin')
    r['category_name'] = _parent_to_resolved_cat.get(pa.strip(), '') if pa else ''

print("=== FINAL get_recommendations RESULT ===")
print(f"Total recs returned: {len(filtered_recs)}")
print()
print("Parent ASIN -> Category Name -> Competitors:")
by_cat = {}
for r in filtered_recs:
    cn = r.get('category_name', 'Unknown')
    pa = r.get('parent_asin') or r.get('asin')
    meta = r.get('metadata') or {}
    n_comp = meta.get('n_competitors', 0) or len(meta.get('competitors', []))
    by_cat.setdefault(cn, []).append((pa, n_comp))

for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    print(f"\n  [{cat}] ({len(items)} products)")
    for pa, nc in items:
        print(f"    - {pa} | {nc} competitors")

print(f"\n=== CATEGORY DROPDOWN WILL SHOW: ===")
for cat in sorted(by_cat.keys()):
    print(f"  - {cat} ({len(by_cat[cat])} products)")
