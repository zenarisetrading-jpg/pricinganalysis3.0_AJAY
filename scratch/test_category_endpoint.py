import os
from dotenv import load_dotenv
load_dotenv()

from features.price_benchmarking.saddl_db import fetch_saddl_categories, fetch_account_products_with_categories
from db import get_supabase_client

account_id = "s2c_test"
supabase = get_supabase_client()

categories = fetch_saddl_categories(account_id)
print("fetch_saddl_categories result length:", len(categories))

resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords").eq("client_id", account_id).execute()
listings = resp.data or []
print("listings length:", len(listings))

saddl_products = fetch_account_products_with_categories(account_id)
print("saddl_products length:", len(saddl_products))

child_to_parent = {p["asin"]: p["parent_asin"] for p in saddl_products}

parent_ref_map = {}
parent_exclude_map = {}
for l in listings:
    p_asin = child_to_parent.get(l["asin"], l["asin"])
    if l.get("reference_name"):
        parent_ref_map[p_asin] = l["reference_name"]
    if l.get("exclude_keywords"):
        parent_exclude_map[p_asin] = l["exclude_keywords"]

asin_categories = {}
for p in saddl_products:
    cat = p.get("category_name")
    if cat:
        asin_categories.setdefault(p["asin"], set()).add(cat)

for c in categories:
    for p in c.get("products", []):
        product_cats = asin_categories.get(p["asin"]) or set()
        p["category_name"] = ", ".join(sorted(list(product_cats)))
        p["reference_name"] = parent_ref_map.get(p["asin"], "")
        p["exclude_keywords"] = parent_exclude_map.get(p["asin"], "")

print("Final categories result length:", len(categories))
print("First category:", categories[0] if categories else None)
