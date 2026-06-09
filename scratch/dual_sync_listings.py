import os
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_account_products_with_categories

def dual_sync():
    sb = get_supabase_client()
    # 1. Clear both
    sb.table('pb_client_listings').delete().eq('client_id', 'oneshot_uae').execute()
    sb.table('pb_client_listings').delete().eq('client_id', 'oneshot-uae').execute()
    
    # 2. Fetch products
    products = fetch_account_products_with_categories('oneshot-uae')
    print(f"Found {len(products)} products for oneshot-uae")
    
    # 3. Create listings for both
    listings = []
    for p in products:
        for cid in ['oneshot_uae', 'oneshot-uae']:
            listings.append({
                'client_id': cid,
                'asin': p['asin'],
                'sku_id': p['asin'],
                'listing_price': p.get('price') or 0.0,
                'marketplace': 'UAE',
                'strategy': 'mid'
            })
    
    if listings:
        sb.table('pb_client_listings').insert(listings).execute()
        print(f"Inserted {len(listings)} listings across both client IDs.")

if __name__ == "__main__":
    dual_sync()
