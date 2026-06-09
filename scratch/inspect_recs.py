import json
import os
import sys

# Add the project root to the python path
sys.path.append(os.getcwd())

from db import get_supabase_client

supabase = get_supabase_client()
client_id = "s2c_uae_test"

resp = (
    supabase.table("pb_recommendations")
    .select("*")
    .eq("client_id", "s2c_test")
    .execute()
)
recs = resp.data or []
print(f"Total recommendations for s2c_test: {len(recs)}")
for r in recs[:15]:
    print(f"ASIN: {r.get('asin')}, Parent: {r.get('parent_asin')}, SKU: {r.get('sku_id')}, Your Price: {r.get('current_price')}, Rec Price: {r.get('recommended_price')}")
