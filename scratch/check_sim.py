
import sys
import os
sys.path.append('.')
from db import get_supabase_client
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis

def run_sim():
    sb = get_supabase_client()
    account_id = 'oneshot_uae'

    # 1. Get your 7 products in this group
    listings = sb.table('pb_client_listings').select('*').eq('client_id', account_id).eq('category_id', '12373047031').execute().data
    products = []
    for l in listings:
        products.append({
            'asin': l['asin'],
            'sku_id': l['asin'],
            'price': l['listing_price'],
            'marketplace': 'UAE',
            'category_id': l['category_id'],
            'strategy': 'mid'
        })

    # 2. Get EXISTING competitors from the DB
    competitors = sb.table('competitor_products').select('competitor_asin, competitor_title, competitor_price').eq('category_id', '12373047031').execute().data

    # 3. Run analysis
    results = calculate_transient_upload_analysis(
        client_id=account_id,
        products=products,
        competitor_records=[{
            'asin': c['competitor_asin'],
            'floor_price': c['competitor_price'],
            'marketplace': 'UAE'
        } for c in competitors]
    )

    # 4. Show results
    print(f"--- SIMULATION RESULTS (Using {len(competitors)} cached competitors) ---")
    for rec in results.get('recommendations', []):
        print(f"ASIN: {rec['asin']} | Current: {rec['current_price']} | New Target: {rec['recommended_price']} | Action: {rec['action']}")

if __name__ == "__main__":
    run_sim()
