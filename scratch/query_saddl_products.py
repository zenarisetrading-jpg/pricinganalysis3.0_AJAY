import os
import sys
from dotenv import load_dotenv

# Ensure we can import features
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

load_dotenv()

def main():
    account_id = "s2c_test"
    print(f"--- Products and Categories for account {account_id} (s2c_test) ---")
    try:
        products = fetch_account_products_with_categories(account_id)
        if products:
            print(f"Found {len(products)} products:")
            for p in products[:15]:
                print(f"SKU: {p.get('sku_id')} | ASIN: {p.get('asin')} | Parent ASIN: {p.get('parent_asin')} | Category: {p.get('category_name')} (ID: {p.get('category_id')})")
            if len(products) > 15:
                print(f"... and {len(products) - 15} more.")
        else:
            print("No products found for this account in SADDL.")
    except Exception as e:
        print(f"Error fetching products: {e}")

if __name__ == "__main__":
    main()
