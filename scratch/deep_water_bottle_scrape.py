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

def calculate_stats(prices):
    if not prices: return 0, 0, 0, 0
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    
    # Median
    if n % 2 == 1:
        median = sorted_prices[n//2]
    else:
        median = (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
        
    mean = sum(prices) / n
    return float(median), float(max(prices)), float(min(prices)), float(mean)

def deep_water_bottle_scrape():
    if not token: return
    client = ApifyClient(token)
    
    print("\n--- STARTING DEEP SCRAPE: 1L STEEL WATER BOTTLE ---")
    actor_id = "vaclavrut/amazon-crawler"
    run_input = {
        "categoryOrProductUrls": [{"url": "https://www.amazon.ae/s?k=1l+steel+water+bottle"}],
        "maxItems": 15,
        "proxyCountry": "AE",
        "useResidentialProxies": True,
        "scrapeProductDetails": True,
        "scrapeSellerInfo": True
    }
    
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        items = client.dataset(run['defaultDatasetId']).list_items().items
        
        all_prices = [i.get('price', {}).get('value') for i in items if isinstance(i.get('price'), dict) and i.get('price', {}).get('value')]
        if not all_prices: 
            print("No prices found.")
            return
        
        median, ceiling, floor, mean = calculate_stats(all_prices)
        
        event_rows = []
        for item in items:
            p_dict = item.get('price', {})
            price = p_dict.get('value') if isinstance(p_dict, dict) else None
            if not price: continue

            # Extract seller - more robustly
            seller = item.get('sellerName') or item.get('brand') or "Amazon.ae"
            
            event_rows.append({
                "asin": item.get('asin'),
                "marketplace": "UAE",
                "event_type": "poll",
                "floor_price": floor,
                "ceiling_price": ceiling,
                "median_price": median,
                "mean_price": mean,
                "n_offers": len(all_prices),
                "buy_box_price": price,
                "seller_name": seller,
                "category_name": "Water Bottles",
                "created_at": datetime.now().isoformat()
            })
            
        if event_rows:
            supabase.table("pb_price_events").insert(event_rows).execute()
            print(f"Success! Deep Scrape complete for {len(event_rows)} water bottles.")
            print(f"Market Stats: Median={median}, Max={ceiling}, Min={floor}")

    except Exception as e:
        print(f"Error during deep scrape: {e}")

if __name__ == "__main__":
    deep_water_bottle_scrape()
