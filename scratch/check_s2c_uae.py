import os
from dotenv import load_dotenv
import sys
from supabase import create_client, Client
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_saddl_categories

load_dotenv('d:/pricing_analysis/.env')

for client_id in ["s2c_test", "s2c-uae"]:
    products = fetch_account_products_with_categories(client_id)
    child_to_parent = {
        p["asin"]: p["parent_asin"]
        for p in products
        if p.get("asin") and p.get("parent_asin")
    }
    parent_asins = {parent for parent in child_to_parent.values() if parent}
    print(f"Total distinct parent ASINs for {client_id}: {len(parent_asins)}")
    
    cats = fetch_saddl_categories(client_id)
    cat_parents = sum([c["asin_count"] for c in cats])
    print(f"Sum of parent ASINs in categories for {client_id}: {cat_parents}")
