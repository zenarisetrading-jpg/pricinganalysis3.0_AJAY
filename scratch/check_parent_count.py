import os
from dotenv import load_dotenv
import sys
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

load_dotenv('d:/pricing_analysis/.env')

client_id = "s2c_test"
products = fetch_account_products_with_categories(client_id)
child_to_parent = {
    p["asin"]: p["parent_asin"]
    for p in products
    if p.get("asin") and p.get("parent_asin")
}
parent_asins = {parent for parent in child_to_parent.values() if parent}
print(f"Total parent ASINs for {client_id}: {len(parent_asins)}")
print("Parent ASINs:", sorted(list(parent_asins)))
