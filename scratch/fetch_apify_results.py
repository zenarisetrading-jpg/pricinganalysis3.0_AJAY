
import requests
import os
import sys
import argparse
from dotenv import load_dotenv

# Fix Python Path
sys.path.append(os.getcwd())

load_dotenv()

API_BASE = "http://127.0.0.1:8000/api/v1/benchmarking"

def fetch_and_push(dataset_id):
    if not dataset_id:
        print("❌ Please provide a dataset_id")
        return

    print(f"🔄 Fetching results for dataset {dataset_id} and pushing to local server...")
    
    try:
        from features.price_benchmarking.apify_client import fetch_dataset_results
        
        items = fetch_dataset_results(dataset_id)
        if not items:
            print("⚠️ Dataset is empty or still processing. Try again in 1 minute.")
            return

        print(f"✅ Found {len(items)} items. Sending to local webhook...")
        
        # Construct the payload that our webhook expects
        payload = {
            "resource": {"defaultDatasetId": dataset_id},
            "meta": {"type": "discovery_scrape", "marketplace": "UAE"}
        }
        
        # POST to our own endpoint
        resp = requests.post(f"{API_BASE}/webhook/apify", json=payload)
        
        if resp.status_code == 200:
            print(f"\n✨ SUCCESS! {len(items)} items processed and saved to your database.")
            print("Refresh your dashboard now to see the analysis for OneShot!")
        else:
            print(f"❌ Failed to process: {resp.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_id", required=True)
    args = parser.parse_args()
    fetch_and_push(args.dataset_id)
