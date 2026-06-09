import os
import sys
from dotenv import load_dotenv

# Ensure we can import features
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from features.price_benchmarking.saddl_db import fetch_saddl_categories

load_dotenv()

def main():
    account_id = "s2c_test"
    print(f"--- Categories Data for '{account_id}' ---")
    try:
        categories = fetch_saddl_categories(account_id)
        for c in categories:
            print(f"\nCategory: {c['category_name']} (ASIN Count: {c['asin_count']}, Avg Rank: {c['avg_rank']})")
            for p in c['products']:
                print(f"  - ASIN: {p['asin']} | Rank: {p['rank']} | Title: {p['title'][:60]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
