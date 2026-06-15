import os
from dotenv import load_dotenv
import sys
from supabase import create_client, Client
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

load_dotenv('d:/pricing_analysis/.env')
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

client_id = "s2c_test"
products = fetch_account_products_with_categories(client_id)
child_to_parent = {
    p["asin"]: p["parent_asin"]
    for p in products
    if p.get("asin") and p.get("parent_asin")
}

res = supabase.table("pb_client_snapshots_daily").select("asin, parent_asin").eq("client_id", client_id).execute()
snapshot_parents = set()
for r in res.data:
    p_asin = child_to_parent.get(r["asin"]) or r.get("parent_asin") or r["asin"]
    snapshot_parents.add(p_asin)

print(f"Total parent ASINs in snapshots for {client_id}: {len(snapshot_parents)}")
print("Parent ASINs:", sorted(list(snapshot_parents)))
