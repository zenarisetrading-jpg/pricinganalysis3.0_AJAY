import os
from apify_client import ApifyClient
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load environment
load_dotenv()
token = os.getenv("APIFY_TOKEN")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def scrape_and_store_top_10():
    if not token:
        print("Error: APIFY_TOKEN not found in .env")
        return

    client = ApifyClient(token)
    categories = [
        {"name": "Coffee Machines", "query": "https://www.amazon.ae/s?k=coffee+machine"},
        {"name": "Headphones", "query": "https://www.amazon.ae/s?k=headphones"},
        {"name": "Backpacks", "query": "https://www.amazon.ae/s?k=backpacks"}
    ]

    actor_id = "vaclavrut/amazon-crawler"
    
    for cat in categories:
        print(f"\n--- SCRAPING TOP 10: {cat['name']} ---")
        run_input = {
            "categoryOrProductUrls": [{"url": cat['query']}],
            "maxItems": 10,
            "proxyCountry": "AE",
            "useResidentialProxies": True
        }
        
        try:
            run = client.actor(actor_id).call(run_input=run_input)
            items = client.dataset(run['defaultDatasetId']).list_items().items
            
            event_rows = []
            for item in items:
                price_val = item.get('price', {})
                if isinstance(price_val, dict):
                    price = price_val.get('value')
                else:
                    price = None
                
                if not price: continue

                # We fill EVERY column possible to avoid NULLs
                event_rows.append({
                    "asin": item.get('asin'),
                    "marketplace": "UAE",
                    "event_type": "poll",
                    "floor_price": price,
                    "buy_box_price": price,
                    "seller_name": item.get('sellerName') or "Amazon",
                    "category_name": cat['name'], # This is our new column
                    "created_at": datetime.now().isoformat()
                })
            
            if event_rows:
                supabase.table("pb_price_events").insert(event_rows).execute()
                print(f"Success! Saved {len(event_rows)} products for {cat['name']}")
            
        except Exception as e:
            print(f"Error scraping {cat['name']}: {e}")

if __name__ == "__main__":
    scrape_and_store_top_10()
