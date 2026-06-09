from features.price_benchmarking.saddl_db import fetch_account_products_with_categories
from db import get_supabase_client
import sys

def sync_listings(account_id="oneshot_uae"):
    print(f"Syncing products for {account_id} to pb_client_listings...")
    products = fetch_account_products_with_categories(account_id)
    if not products:
        print("No products found in bsr_history.")
        return

    sb = get_supabase_client()
    listings = []
    for p in products:
        listings.append({
            "asin": p["asin"],
            "client_id": account_id,
            "marketplace": "UAE", # Default for oneshot_uae
            "listing_price": 99.00, # Dummy price
            "category_id": p["category_id"],
            "strategy": "mid"
        })
    
    if listings:
        res = sb.table("pb_client_listings").upsert(listings, on_conflict="client_id,asin,marketplace").execute()
        print(f"✅ Successfully synced {len(listings)} products to pb_client_listings.")
    else:
        print("No listings to sync.")

if __name__ == "__main__":
    sync_listings()
