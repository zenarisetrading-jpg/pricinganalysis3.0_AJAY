
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://127.0.0.1:8000/api/v1/benchmarking"
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "saddl_secret_token_123")
# Use the correct technical IDs found in SADDL
SADDL_MARKETPLACE_IDS = ['A2VIGQ35RCS4UG', 'A17E79C6D8DWNP']

def test_apify_trigger():
    print(f"Fetching categories for OneShot using IDs {SADDL_MARKETPLACE_IDS}...")
    try:
        # We need to call the API with the ID that SADDL understands
        # For testing, we'll try the first ID
        target_id = SADDL_MARKETPLACE_IDS[1] # Seller ID usually has better category data
        
        resp = requests.get(f"{API_BASE}/account-bsr-categories?account_id={target_id}")
        resp.raise_for_status()
        categories = resp.json().get("categories", [])
        
        if not categories:
            print(f"No categories found for {target_id}. Trying {SADDL_MARKETPLACE_IDS[0]}...")
            resp = requests.get(f"{API_BASE}/account-bsr-categories?account_id={SADDL_MARKETPLACE_IDS[0]}")
            categories = resp.json().get("categories", [])

        if not categories:
            print("❌ Still no categories found. Please check your SADDL database connection.")
            return

        test_cat = categories[0]["category_name"]
        print(f"✅ Selected category for test: {test_cat}")

        payload = {
            "category_name": test_cat,
            "marketplace": "UAE",
            "max_items": 10
        }
        
        headers = {"X-Internal-Token": INTERNAL_TOKEN, "Content-Type": "application/json"}
        trigger_resp = requests.post(f"{API_BASE}/trigger-category-scrape", json=payload, headers=headers)
        trigger_resp.raise_for_status()
        
        print("\n✨ Scrape Triggered Successfully!")
        print(f"Dataset ID: {trigger_resp.json().get('dataset_id')}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_apify_trigger()
