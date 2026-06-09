import os
from datetime import datetime, timezone
from db import get_supabase_client
from features.price_benchmarking.discovery_service import fetch_account_products_with_categories, fetch_parent_asin_categories, fetch_competitors_by_category
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis
from features.price_benchmarking.relevance_filter import filter_related_products

def debug_sync():
    sb = get_supabase_client()
    account_id = "oneshot_uae"
    marketplace = "UAE"
    
    # 1. Fetch REAL products
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        print("No products found")
        return

    # 2. Pick the first parent to test
    p = products_data[0]
    parent_asin = p["parent_asin"]
    print(f"Testing with Parent ASIN: {parent_asin}")
    
    # 3. Fetch Real Competitors
    categories = fetch_parent_asin_categories(account_id, parent_asin)
    cat_id = categories[0]["category_id"] if categories else None
    raw_competitors = fetch_competitors_by_category(cat_id, marketplace)
    print(f"Found {len(raw_competitors)} raw competitors")
    
    # 4. Filter
    filtered = filter_related_products(p, raw_competitors)
    print(f"Filtered to {len(filtered)} relevant competitors")
    
    # 5. Analyze
    analysis_products = [{
        "asin": p["asin"],
        "sku_id": p["asin"],
        "price": p.get("price") or 0.0,
        "marketplace": marketplace,
        "category_id": cat_id,
        "strategy": "mid",
        "parent_asin": parent_asin
    }]
    
    results = calculate_transient_upload_analysis(
        client_id=account_id,
        products=analysis_products,
        competitor_records=filtered
    )
    
    recs = results.get("recommendations", [])
    print(f"Generated {len(recs)} recommendations")
    
    if recs:
        # Try to insert and CATCH ERROR
        try:
            res = sb.table("pb_recommendations").insert(recs).execute()
            print(f"SUCCESS: Inserted {len(res.data)} records")
        except Exception as e:
            print(f"DATABASE ERROR: {str(e)}")

if __name__ == "__main__":
    debug_sync()
