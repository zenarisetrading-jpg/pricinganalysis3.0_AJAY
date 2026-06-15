
import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
AMAZON_ACTOR_ID = "junglee/amazon-crawler"

def test_live_apify():
    if not APIFY_TOKEN:
        print("❌ APIFY_TOKEN not found in .env")
        return

    print(f"Connecting to Apify with token: {APIFY_TOKEN[:10]}...")
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "asins": ["B076MBM69K"], # Test ASIN
        "domain": "amazon.ae",
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyCountry": "AE"
        },
        "maxItems": 1
    }

    print(f"Triggering actor {AMAZON_ACTOR_ID}...")
    try:
        # We use .start() instead of .call() for a faster test
        run = client.actor(AMAZON_ACTOR_ID).start(run_input=run_input)
        print(f"✅ SUCCESS! Actor started.")
        print(f"Run ID: {run['id']}")
        print(f"Dataset ID: {run['defaultDatasetId']}")
    except Exception as e:
        print(f"❌ APIFY ERROR: {e}")

if __name__ == "__main__":
    test_live_apify()
