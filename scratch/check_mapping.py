import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

load_dotenv('d:/pricing_analysis/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

asins = ["B0DSG94PG1", "B0FWKLG3JJ", "B0FWKSMV4J"]
client_id = "s2c_test"

print("--- saddl_db fetch_account_products_with_categories ---")
products = fetch_account_products_with_categories(client_id)
child_to_parent = {}
for p in products:
    child_to_parent[p["asin"]] = p["parent_asin"]
    if p["parent_asin"] in asins or p["asin"] in asins:
        print(f"SADDL Mapping: child={p['asin']}, parent={p['parent_asin']}, category={p['category_name']}")

print("--- pb_client_snapshots_daily ---")
res = supabase.table("pb_client_snapshots_daily").select("asin, parent_asin, snapshot_date").eq("client_id", client_id).execute()
for r in res.data:
    p_asin = child_to_parent.get(r["asin"]) or r.get("parent_asin") or r["asin"]
    if p_asin in asins or r["asin"] in asins:
        print(f"Snapshot: asin={r['asin']}, stored_parent={r.get('parent_asin')}, mapped_parent={p_asin}")

