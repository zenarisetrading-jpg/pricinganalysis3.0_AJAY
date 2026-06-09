import os
import sys
from dotenv import load_dotenv

# Add parent dir to path to import features
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from features.price_benchmarking.saddl_db import fetch_saddl_accounts, fetch_saddl_categories

load_dotenv()

def get_live_data():
    print("--- FETCHING SADDL ACTIVE ACCOUNTS ---")
    accounts = fetch_saddl_accounts()
    
    if not accounts:
        print("No SADDL accounts found or connection failed.")
        return

    print(f"Found {len(accounts)} active accounts:\n")
    
    for acc in accounts:
        acc_id = acc['account_id']
        acc_name = acc['account_name']
        print(f"ACCOUNT: {acc_name} ({acc_id})")
        
        categories = fetch_saddl_categories(acc_id)
        if not categories:
            print("  No categories or products found for this account.")
        else:
            for cat in categories:
                print(f"  Category: {cat['category_name']} | Product Count: {cat['asin_count']} | Avg Rank: {cat['avg_rank']:.2f}")
                products = cat['products']
                for p in products[:5]: # Show first 5 products
                    print(f"    - {p['title'][:50]}... ({p['asin']}) [Rank: #{p['rank']:.0f}]")
                if len(products) > 5:
                    print(f"    ... and {len(products)-5} more products")
        print("-" * 40)

if __name__ == "__main__":
    get_live_data()
