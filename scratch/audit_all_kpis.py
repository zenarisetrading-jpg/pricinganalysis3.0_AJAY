import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client
from features.price_benchmarking.saddl_db import (
    fetch_saddl_accounts, fetch_account_products_with_categories, fetch_saddl_categories
)
from features.price_benchmarking.snapshot_service import _resolve_majority_categories

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

def latest_snapshots_by_parent(rows, child_to_parent):
    parent_map = {}
    for r in rows:
        child_asin = r.get('asin')
        parent = child_to_parent.get(child_asin, child_asin)
        r['parent_asin'] = parent
        if parent not in parent_map or r.get('snapshot_date', '') > parent_map[parent].get('snapshot_date', ''):
            parent_map[parent] = r
    return list(parent_map.values())

accounts = fetch_saddl_accounts()
print("=" * 80)
print(f"{'ACCOUNT':<22} {'Tracked ASINs':>14} {'Snap Rows':>10} {'Avg Mkt Idx':>12} {'Health':>8} {'Issues'}")
print("=" * 80)

for account in accounts:
    account_id = account['client_id']
    acct_name = account['client_name']

    issues = []

    # --- Pull snapshots ---
    resp = sb.table('pb_client_snapshots_daily').select('*').eq('client_id', account_id).order('snapshot_date', desc=True).execute()
    all_rows = resp.data or []

    if not all_rows:
        print(f"  {acct_name[:20]:<22} {'NO SNAPSHOTS':>14}")
        continue

    # --- Build parent map from SADDL ---
    try:
        saddl_products = fetch_account_products_with_categories(account_id)
        child_to_parent = {
            p['asin']: p['parent_asin']
            for p in saddl_products
            if p.get('asin') and p.get('parent_asin')
        }
        categories = fetch_saddl_categories(account_id)
    except Exception as e:
        print(f"  {acct_name[:20]:<22} SADDL error: {e}")
        continue

    # --- Resolve majority categories ---
    saddl_products = _resolve_majority_categories(saddl_products)
    parent_to_resolved_category = {}
    for p in saddl_products:
        parent = p.get('parent_asin')
        cat_name = p.get('category_name')
        if parent and cat_name:
            parent_to_resolved_category[parent.strip()] = cat_name.strip()

    filtered_categories = []
    for c in categories:
        c_name_norm = c['category_name'].strip().lower()
        filtered_products = []
        for p in c.get('products', []):
            parent = p.get('asin')
            if parent:
                resolved_cat = parent_to_resolved_category.get(parent.strip())
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

    parent_asin_count = sum([c['asin_count'] for c in filtered_categories])

    # BSR parent ASINs set
    bsr_parent_asins = set()
    for c in filtered_categories:
        for p in c.get('products', []):
            pa = p.get('asin')
            if pa:
                bsr_parent_asins.add(pa.strip())

    # --- Get latest snapshot per parent, filtered to BSR set ---
    snapshot_rows = latest_snapshots_by_parent(all_rows, child_to_parent)
    if bsr_parent_asins:
        snapshot_rows = [
            r for r in snapshot_rows
            if (r.get('parent_asin') or r.get('asin')) in bsr_parent_asins
        ]

    n_snaps = len(snapshot_rows)

    # --- Avg Market Index ---
    valid_indices = []
    for r in snapshot_rows:
        val = None
        raw = r.get('index_vs_median')
        if raw is not None:
            try:
                val = float(raw)
            except:
                pass
        if (val is None or val == 0):
            yp = float(r.get('your_price') or 0)
            mp = float(r.get('median_price') or 0)
            if yp > 0 and mp > 0:
                val = (yp / mp) * 100
        if val and val != 0:
            valid_indices.append(val)

    avg_index = sum(valid_indices) / len(valid_indices) if valid_indices else 0
    if len(valid_indices) < n_snaps:
        issues.append(f"{n_snaps - len(valid_indices)} snaps missing index/prices")

    # --- Health Score ---
    healthy_zones = ['budget', 'value', 'mid_market', 'premium']
    healthy_count = sum(1 for r in snapshot_rows if r.get('zone') in healthy_zones)
    health_score = round((healthy_count / n_snaps) * 100) if n_snaps > 0 else 0

    # Check for missing zone data
    no_zone = sum(1 for r in snapshot_rows if not r.get('zone'))
    if no_zone:
        issues.append(f"{no_zone} snaps missing zone")

    # Consistency check: parent_asin_count vs snapshot rows
    if parent_asin_count != n_snaps:
        issues.append(f"BSR count={parent_asin_count} but snaps={n_snaps}")

    issue_str = '; '.join(issues) if issues else 'OK'
    flag = ' ⚠' if issues else ' ✓'

    print(f"  {acct_name[:20]:<22} {parent_asin_count:>14} {n_snaps:>10} {avg_index:>11.1f}% {health_score:>7}%  {flag} {issue_str}")

print()
print("=" * 80)
print()

# --- Detailed per-account breakdown for accounts with issues ---
print("\n=== DETAILED BREAKDOWN PER ACCOUNT ===\n")
for account in accounts:
    account_id = account['client_id']
    acct_name = account['client_name']

    resp = sb.table('pb_client_snapshots_daily').select('*').eq('client_id', account_id).order('snapshot_date', desc=True).execute()
    all_rows = resp.data or []
    if not all_rows:
        continue

    try:
        saddl_products = fetch_account_products_with_categories(account_id)
        categories = fetch_saddl_categories(account_id)
    except:
        continue

    child_to_parent = {p['asin']: p['parent_asin'] for p in saddl_products if p.get('asin') and p.get('parent_asin')}
    saddl_products = _resolve_majority_categories(saddl_products)
    parent_to_cat = {p['parent_asin'].strip(): p['category_name'].strip() for p in saddl_products if p.get('parent_asin') and p.get('category_name')}

    filtered_categories = []
    for c in categories:
        c_name_norm = c['category_name'].strip().lower()
        fp = [p for p in c.get('products', []) if p.get('asin') and
              (not parent_to_cat.get(p['asin'].strip()) or parent_to_cat.get(p['asin'].strip(), '').lower() == c_name_norm)]
        if fp:
            c['products'] = fp
            c['asin_count'] = len(fp)
            filtered_categories.append(c)

    bsr_parent_asins = {p.get('asin').strip() for c in filtered_categories for p in c.get('products', []) if p.get('asin')}
    snapshot_rows = latest_snapshots_by_parent(all_rows, child_to_parent)
    if bsr_parent_asins:
        snapshot_rows = [r for r in snapshot_rows if (r.get('parent_asin') or r.get('asin')) in bsr_parent_asins]

    if not snapshot_rows:
        continue

    print(f"{'─'*60}")
    print(f"  {acct_name} ({account_id}) — {len(snapshot_rows)} tracked parent ASINs")
    print(f"{'─'*60}")
    print(f"  {'Parent ASIN':<16} {'Category':<26} {'Zone':<15} {'Your P':>8} {'Med P':>8} {'Idx':>7}")
    for r in sorted(snapshot_rows, key=lambda x: parent_to_cat.get((x.get('parent_asin') or x.get('asin', '')).strip(), 'zzz')):
        pa = (r.get('parent_asin') or r.get('asin', ''))[:16]
        cat = parent_to_cat.get((r.get('parent_asin') or r.get('asin', '')).strip(), '?')[:25]
        zone = r.get('zone', '?')[:14]
        yp = float(r.get('your_price') or 0)
        mp = float(r.get('median_price') or 0)
        idx = float(r.get('index_vs_median') or 0)
        if idx == 0 and yp > 0 and mp > 0:
            idx = (yp / mp) * 100
        flag = ' ⚠' if zone not in ['budget', 'value', 'mid_market', 'premium', 'no_competitors'] else ''
        print(f"  {pa:<16} {cat:<26} {zone:<15} {yp:>8.2f} {mp:>8.2f} {idx:>6.1f}%{flag}")
    print()
