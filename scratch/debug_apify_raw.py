
import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def debug_raw():
    token = os.getenv("APIFY_TOKEN")
    dataset_id = "7DGkd00qC20r01j2N" # Your latest dataset
    
    if not token:
        print("❌ No APIFY_TOKEN")
        return

    client = ApifyClient(token)
    print(f"🔍 Fetching raw items from dataset {dataset_id}...")
    items = client.dataset(dataset_id).list_items(limit=2).items
    
    if not items:
        print("⚠️ Dataset is empty or ID is wrong.")
        return

    print("\n--- RAW ITEM 1 ---")
    print(json.dumps(items[0], indent=2))
    
    print("\n--- RAW ITEM 2 ---")
    print(json.dumps(items[1], indent=2))

if __name__ == "__main__":
    debug_raw()
