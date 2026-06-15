import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

client_id = 's2c_test'
products = fetch_account_products_with_categories(client_id)
child_to_parent = {p['asin']: p['parent_asin'] for p in products if p.get('asin') and p.get('parent_asin')}
parent_asins = set(child_to_parent.values())

# Check snapshots
res = sb.table('pb_client_snapshots_daily').select('asin, parent_asin, snapshot_date, n_competitors, zone').eq('client_id', client_id).order('snapshot_date', desc=True).execute()
snapshot_rows = res.data or []

snapshot_parent_map = {}
for r in snapshot_rows:
    key = child_to_parent.get(r['asin']) or r.get('parent_asin') or r['asin']
    if key not in snapshot_parent_map:
        snapshot_parent_map[key] = r

print("=== SNAPSHOT VERIFICATION ===")
print("Total unique parent ASINs in SADDL:    " + str(len(parent_asins)))
print("Unique parent ASINs with snapshots:    " + str(len(snapshot_parent_map)))
print()
print("All parent ASINs with snapshots:")
for pa in sorted(snapshot_parent_map.keys()):
    r = snapshot_parent_map[pa]
    date = r.get('snapshot_date', 'N/A')
    comps = r.get('n_competitors', 0)
    zone = r.get('zone', 'N/A')
    print("  " + pa + " | " + str(date) + " | competitors: " + str(comps) + " | zone: " + str(zone))

missing = parent_asins - set(snapshot_parent_map.keys())
print("\nStill missing: " + str(len(missing)))
for pa in sorted(missing):
    print("  - " + pa)

# Check recommendations
res2 = sb.table('pb_recommendations').select('asin, parent_asin').eq('client_id', client_id).eq('status', 'pending').execute()
rec_parents = set((r.get('parent_asin') or r['asin']) for r in (res2.data or []))
print("\nUnique parent ASINs with pending recommendations: " + str(len(rec_parents)))
