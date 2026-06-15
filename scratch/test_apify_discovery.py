import os
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load the API token from .env
load_dotenv()
token = os.getenv("APIFY_TOKEN")

def clean_text(text):
    if not text: return ""
    # Remove non-ascii characters to avoid Windows encoding errors
    return "".join(i for i in text if ord(i) < 128)

def test_apify_discovery():
    if not token:
        print("Error: APIFY_TOKEN not found in .env")
        return

    client = ApifyClient(token)
    
    print("Connecting to Apify...")
    try:
        # Search for "Coffee Machine" on Amazon.ae to discover competitors
        print("\nTesting Competitor Discovery for 'Coffee Machine' on Amazon.ae...")
        actor_id = "vaclavrut/amazon-crawler"
        run_input = {
            "categoryOrProductUrls": [{"url": "https://www.amazon.ae/s?k=coffee+machine"}],
            "maxItems": 10,
            "proxyCountry": "AE",
            "useResidentialProxies": True
        }
        
        print("Triggering discovery run (this may take 1-2 minutes)...")
        run = client.actor(actor_id).call(run_input=run_input)
        
        print(f"Run finished! Fetching results from dataset: {run['defaultDatasetId']}")
        items = client.dataset(run['defaultDatasetId']).list_items().items
        
        if items:
            print(f"\n--- DISCOVERED {len(items)} PRODUCTS ---")
            for i, item in enumerate(items):
                asin = item.get('asin')
                title = clean_text(item.get('title'))[:60]
                price_data = item.get('price')
                
                if isinstance(price_data, dict):
                    price = f"{price_data.get('value')} {price_data.get('currency')}"
                else:
                    price = "Unknown"
                
                seller = clean_text(item.get('sellerName')) or "Unknown"
                
                print(f"{i+1}. [{asin}] {title}...")
                print(f"   Price: {price} | Seller: {seller}")
                print("-" * 50)
        else:
            print("Warning: No items found. Amazon might be blocking the search results.")
            
    except Exception as e:
        print(f"Error during discovery test: {e}")

if __name__ == "__main__":
    test_apify_discovery()
