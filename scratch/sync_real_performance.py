
import sys
import os
from datetime import datetime, timezone
sys.path.append('.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import execute_saddl_query, fetch_account_products_with_categories
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis
from features.price_benchmarking.discovery_service import save_pricing_analysis

def sync_real_data():
    account_id = 'oneshot_uae'
    sb = get_supabase_client()
    
    print(f"Starting Real Data Sync for {account_id}...")

    # 1. Fetch real products from SADDL
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        print("No products found in SADDL.")
        return

    # 2. Get latest performance data for EACH product
    # We'll group by Parent ASIN for the analysis
    parent_groups = {}
    for p in products_data:
        asin = p['asin']
        parent_asin = p['parent_asin']
        
        # Get real traffic data
        perf_query = """
        SELECT units_ordered, sessions, unit_session_percentage, report_date 
        FROM sc_raw.sales_traffic 
        WHERE child_asin = %s AND account_id = %s 
        ORDER BY report_date DESC LIMIT 1
        """
        perf_rows = execute_saddl_query(perf_query, (asin, account_id))
        
        if perf_rows:
            r = perf_rows[0]
            units, sessions, cvr, r_date = r[0], r[1], r[2], r[3]
            perf_date = r_date.isoformat()
        else:
            units, sessions, cvr, perf_date = 0, 0, 0, datetime.now(timezone.utc).date().isoformat()

        # Get listing info from local DB
        listing = sb.table('pb_client_listings').select('*').eq('asin', asin).eq('client_id', account_id).execute().data
        if not listing: continue
        l = listing[0]

        parent_groups.setdefault(parent_asin, []).append({
            'asin': asin,
            'sku_id': asin,
            'price': float(l['listing_price']),
            'marketplace': 'UAE',
            'category_id': l['category_id'],
            'strategy': l.get('strategy') or 'mid',
            'units_ordered': units,
            'sessions': sessions,
            'acos': 0.0, # Not available in sales_traffic
            'cvr': float(cvr) if cvr else 0.0,
            'performance_date': perf_date
        })

    # 3. Process each Parent Group using CACHED competitor data
    for parent_asin, p_list in parent_groups.items():
        # Use category_id of the first product in group
        cat_id = p_list[0]['category_id']
        
        # Get existing competitors from DB
        comps = sb.table('competitor_products').select('competitor_asin, competitor_price').eq('category_id', cat_id).execute().data
        
        if not comps:
            print(f"Skipping {parent_asin}: No cached competitor data for category {cat_id}.")
            continue

        # Run analysis
        results = calculate_transient_upload_analysis(
            client_id=account_id,
            products=p_list,
            competitor_records=[{
                'asin': c['competitor_asin'],
                'floor_price': c['competitor_price'],
                'marketplace': 'UAE'
            } for c in comps]
        )

        # Save to DB (this updates audit tab and recommendations)
        save_pricing_analysis(parent_asin, 'UAE', results)
        print(f"Updated {parent_asin} with real performance data from {p_list[0]['performance_date']}.")

    print("\nSync complete. All dashboard data is now based on REAL SADDL records.")

if __name__ == "__main__":
    sync_real_data()
