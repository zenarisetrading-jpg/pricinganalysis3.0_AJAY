import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

def main():
    products = fetch_account_products_with_categories("s2c_test")
    print(f"Total products in SADDL DB for s2c_test: {len(products)}")
    for p in products:
        print(p)

if __name__ == "__main__":
    main()
