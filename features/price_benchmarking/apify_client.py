
import os
import re
from typing import List, Dict, Optional
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
APP_URL = os.environ.get("APP_URL")

client = None
if APIFY_TOKEN:
    client = ApifyClient(APIFY_TOKEN)
else:
    print("WARNING: APIFY_TOKEN not found in environment variables!")

# Use the most reliable actor for UAE/KSA as per PRD
AMAZON_ACTOR_ID = "junglee/amazon-crawler"

def trigger_price_scrape(asins: List[str], marketplace: str, client_id: str = None) -> str:

    if not client:
        raise ValueError("APIFY_TOKEN environment variable not set")

    country_code = "AE" if marketplace == "UAE" else "SA"
    domain = "amazon.ae" if marketplace == "UAE" else "amazon.sa"
    
    product_urls = [{"url": f"https://www.{domain}/dp/{asin}"} for asin in asins]
    
    run_input = {
        "categoryOrProductUrls": product_urls,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
            "apifyProxyCountry": country_code
        },
        "maxItems": len(asins) if asins else 100,
        "waitMs": 3000
    }
    
    # Only configure Webhook if we have a public APP_URL
    webhook_config = []
    if APP_URL and "localhost" not in APP_URL and "127.0.0.1" not in APP_URL:
        meta_payload = f'{{"type": "price_scrape", "marketplace": "{marketplace}"'
        if client_id:
            meta_payload += f', "client_id": "{client_id}"'
        meta_payload += '}'
        
        webhook_config = [
            {
                "event_types": ["ACTOR.RUN.SUCCEEDED"],
                "request_url": f"{APP_URL.rstrip('/')}/api/v1/benchmarking/webhook/apify",
                "payload_template": "{\"resource\": {\"defaultDatasetId\": \"{{defaultDatasetId}}\"}, \"meta\": " + meta_payload + "}"
            }
        ]
    else:
        print("Local environment detected: Skipping Apify webhook (no public APP_URL found).")
    
    run = client.actor(AMAZON_ACTOR_ID).call(run_input=run_input, webhooks=webhook_config)
    return run["defaultDatasetId"]


def trigger_category_discovery(category_url: str, marketplace: str, category_id: int, account_id: str, max_items: int = 100) -> str:

    from apify_client import ApifyClient
    client = ApifyClient(os.environ.get("APIFY_TOKEN"))
    
    # Using the Amazon Product Scraper for category pages
    run_input = {
        "categoryOrProductUrls": [{"url": category_url}],
        "maxItems": max_items,
        "proxyConfiguration": {"useApifyProxy": True},
        "locationCode": "ae" if marketplace == "UAE" else "us"
    }
    
    # Configure Webhook only if we have a public URL
    webhooks = []
    webhook_base = os.environ.get('WEBHOOK_BASE_URL') or os.environ.get('APP_URL')
    if webhook_base and "localhost" not in webhook_base and "127.0.0.1" not in webhook_base:
        webhooks = [{
            "event_types": ["ACTOR.RUN.SUCCEEDED"],
            "request_url": f"{webhook_base.rstrip('/')}/api/v1/benchmarking/webhook/apify",
            "payload_template": "{\"datasetId\": \"{{resource.defaultDatasetId}}\", \"meta\": {\"type\": \"discovery_scrape\", \"marketplace\": \"" + marketplace + "\", \"category_id\": " + str(category_id) + ", \"account_id\": \"" + account_id + "\"}}"
        }]
    else:
        print(f"Local environment or missing URL: Skipping Apify webhook for category {category_id}.")
    
    # Start the actor
    run = client.actor("junglee/amazon-crawler").start(
        run_input=run_input,
        webhooks=webhooks
    )
    return run["id"], run["defaultDatasetId"]


def poll_for_results(run_id: str, timeout_mins: int = 15) -> List[Dict]:
    """Poll for Apify run completion and fetch results."""

    import time
    from apify_client import ApifyClient
    client = ApifyClient(os.environ.get("APIFY_TOKEN"))
    
    start_time = time.time()
    while time.time() - start_time < timeout_mins * 60:
        run = client.run(run_id).get()
        status = run.get("status")
        
        if status == "SUCCEEDED":
            dataset_id = run.get("defaultDatasetId")
            return fetch_dataset_results(dataset_id)
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            print(f"Apify run {run_id} failed with status: {status}")
            return []
            
        print(f"Waiting for Apify run {run_id} (status: {status})...")
        time.sleep(20) # Poll every 20 seconds
        
    print(f"Apify run {run_id} timed out after {timeout_mins} minutes.")
    return []


def trigger_search_discovery(query: str, marketplace: str, max_items: int = 100) -> str:
    domain = "amazon.ae" if marketplace == "UAE" else "amazon.sa"
    search_url = f"https://www.{domain}/s?k={query.replace(' ', '+')}"
    run_id, dataset_id = trigger_category_discovery(search_url, marketplace, 0, "", max_items)
    return dataset_id


def fetch_dataset_results(dataset_id: str) -> List[Dict]:

    if not client:
        raise ValueError("APIFY_TOKEN environment variable not set")
    dataset = client.dataset(dataset_id)
    items = dataset.list_items().items
    return items


def parse_apify_item(item: Dict, marketplace: str) -> Dict:
    # 1. FIND ASIN & PARENT ASIN
    asin = item.get("asin")
    parent_asin = item.get("parentAsin") or item.get("parent_asin")
    
    if not asin:
        url_text = item.get("url") or item.get("unNormalizedProductUrl") or item.get("input")
        if url_text:
            import re
            m = re.search(r'/dp/([A-Z0-9]{10})', url_text)
            if m:
                asin = m.group(1)
                
    # 2. FIND PRICE (Deep search)
    price = item.get("price") or item.get("currentPrice") or item.get("priceValue") or item.get("listPrice")
    
    # Try Variant list
    if not price and item.get("variantDetails"):
        for v in item["variantDetails"]:
            if v.get("price"):
                price = v["price"]
                break
    
    # Try Offers list
    if not price and item.get("offers") and len(item["offers"]) > 0:
        price = item["offers"][0].get("price")
        
    # Try A+ Content fallback
    if not price and item.get("aPlusContent"):
        raw_text = item["aPlusContent"].get("rawText", "")
        import re
        m = re.search(r'AED\s*(\d+\.?\d*)', raw_text)
        if m:
            price = m.group(1)

    # DETECTIVE LOGGING: If still no price, print values to see what's there
    if not price:
        detective_fields = {k: item[k] for k in ["price", "listPrice", "currentPrice", "inStock", "inStockText"] if k in item}
        print(f"Detective ASIN {asin}: {detective_fields}")
            
    # 3. CONVERT PRICE TO FLOAT
    floor_price = None
    if price:
        if isinstance(price, (int, float)):
            floor_price = float(price)
        elif isinstance(price, dict):
            # Handle { "value": 25.99, "currency": "AED" }
            val = price.get("value") or price.get("amount") or price.get("price")
            if val:
                floor_price = float(val)
        elif isinstance(price, str):
            import re
            clean = price.replace(',', '')
            m = re.search(r'(\d+\.?\d*)', clean)
            if m:
                floor_price = float(m.group(1))
                
    # 4. FIND SELLER
    seller_name = item.get("sellerName")
    seller_obj = item.get("seller")
    if not seller_name and isinstance(seller_obj, dict):
        seller_name = seller_obj.get("name")
        
    # 5. SANITIZE SHIPPING
    shipping_price = item.get("shippingPrice")
    clean_shipping = 0.0
    if shipping_price:
        if isinstance(shipping_price, (int, float)):
            clean_shipping = float(shipping_price)
        elif isinstance(shipping_price, dict):
            val = shipping_price.get("value") or shipping_price.get("amount")
            if val:
                clean_shipping = float(val)
        elif isinstance(shipping_price, str):
            import re
            m = re.search(r'(\d+\.?\d*)', shipping_price.replace(',', ''))
            if m:
                clean_shipping = float(m.group(1))
                
    # 6. FIND CATEGORY
    category_name = "Unknown"
    breadcrumbs = item.get("breadCrumbs")
    if breadcrumbs and isinstance(breadcrumbs, list) and len(breadcrumbs) > 0:
        category_name = breadcrumbs[-1].get("title") or breadcrumbs[-1].get("name") or "Unknown"
        
    return {
        "asin": asin,
        "parent_asin": parent_asin,
        "title": item.get("title") or item.get("name") or asin,
        "marketplace": marketplace,
        "floor_price": floor_price,
        "buy_box_price": floor_price if item.get("isBuyBoxWinner") else None,
        "seller_name": seller_name or "Unknown",
        "is_buy_box_winner": item.get("isBuyBoxWinner", False),
        "shipping_price": clean_shipping,
        "category_name": category_name,
        "rating": item.get("stars") or item.get("rating"),
        "reviews": item.get("reviewsCount") or item.get("reviews"),
        "sales_rank": item.get("salesRank") or item.get("rank"),
        "brand": item.get("brand"),
        "url": item.get("url"),
        "event_type": "poll"
    }
