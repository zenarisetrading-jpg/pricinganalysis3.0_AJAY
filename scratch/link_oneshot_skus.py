import sys
import os
sys.path.append(os.getcwd())
from db import get_supabase_client

def link_skus():
    s = get_supabase_client()
    client_id = "oneshot_uae"
    
    print(f"🔗 Linking products for {client_id}...")
    
    # 0. Ensure Category exists
    s.table("pb_categories").upsert({
        "id": 6,
        "name": "UAE Discovery",
        "marketplace": "UAE",
        "keepa_cat_id": 999006
    }, on_conflict="id").execute()
    
    # 1. Get all ASINs we just scraped that have prices
    events = s.table("pb_price_events").select("asin, floor_price").eq("marketplace", "UAE").execute()
    
    # Map ASIN to its price
    asin_to_price = {r["asin"]: r["floor_price"] for r in events.data if r["floor_price"]}
    asins = list(asin_to_price.keys())
    
    if not asins:
        print("❌ No price events found! Run fetch_apify_results.py first.")
        return

    print(f"📦 Found {len(asins)} unique products with prices.")
    
    # 2. Register them as Benchmarking SKUs
    sku_rows = []
    for asin in asins:
        sku_rows.append({
            "client_id": client_id,
            "asin": asin,
            "sku_id": f"SKU-{asin}", 
            "product_title": f"Product {asin}",
            "is_active": True,
            "strategy": "mid",
            "fallback_price": asin_to_price[asin],
            "category_id": 6 # Using the ID for UAE Discovery
        })
    
    # 3. Upsert into pb_benchmarking_skus
    s.table("pb_benchmarking_skus").upsert(sku_rows, on_conflict="client_id,asin").execute()
    
    # 4. ALSO populate pb_category_competitors so the benchmark logic has something to compare against
    competitor_rows = []
    for asin in asins:
        competitor_rows.append({
            "category_id": 6,
            "asin": asin,
            "marketplace": "UAE",
            "source": "apify_search",
            "is_active": True,
            "title": f"Competitor {asin}"
        })
    s.table("pb_category_competitors").upsert(competitor_rows, on_conflict="category_id,asin").execute()
    
    print(f"✅ Successfully linked {len(sku_rows)} products and added them to the competitor pool!")

if __name__ == "__main__":
    link_skus()
