import os
from datetime import datetime, timedelta, timezone
from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis
from features.price_benchmarking.discovery_service import save_pricing_analysis

def force_analysis(account_id="oneshot_uae"):
    print(f"Forcing analysis recalculation for {account_id}...")
    sb = get_supabase_client()
    
    # 1. Fetch our products
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        print("No products found for this account.")
        return

    # Group by category
    unique_categories = {}
    for p in products_data:
        cat_id = p["category_id"]
        if not cat_id: continue
        unique_categories.setdefault(cat_id, []).append(p)

    for cat_id, cat_products in unique_categories.items():
        print(f"Processing category {cat_id}...")
        
        # 2. Fetch competitor data we already have
<<<<<<< HEAD
        from features.price_benchmarking.saddl_db import fetch_competitor_pricing_by_category
        raw_competitors = fetch_competitor_pricing_by_category(cat_id, "UAE")
=======
        comp_resp = sb.table("competitor_products").select("*").eq("category_id", cat_id).execute()
        raw_competitors = comp_resp.data
>>>>>>> 5021546c74a8a9e0d82812ff2d0468e014ba5e35
        if not raw_competitors:
            print(f"No competitor data found for category {cat_id}. Skipping.")
            continue
            
        # Map DB columns to what analysis expects
        competitors = []
        for c in raw_competitors:
            if c.get("competitor_price") is None: continue
            competitors.append({
                "asin": c["competitor_asin"],
                "price": float(c["competitor_price"]),
                "title": c.get("competitor_title") or c["competitor_asin"],
                "marketplace": c.get("marketplace") or "UAE",
                "category_id": c.get("category_id")
            })
        
        print(f"Found {len(competitors)} competitors for category {cat_id}.")

        # 3. Prepare our products for analysis
        analysis_products = []
        for p in cat_products:
            listing = sb.table("pb_client_listings").select("*").eq("asin", p["asin"]).execute()
            if listing.data:
                l = listing.data[0]
                analysis_products.append({
                    "asin": p["asin"],
                    "sku_id": p["asin"],
                    "price": float(l["listing_price"]) if l.get("listing_price") is not None else 0.0,
                    "marketplace": "UAE",
                    "category_id": cat_id,
                    "strategy": l.get("strategy") or "mid",
                    "min_price": float(l["min_price"]) if l.get("min_price") else None,
                    "max_price": float(l["max_price"]) if l.get("max_price") else None,
                })
        
        if not analysis_products:
            print(f"No active listings found for category {cat_id} in pb_client_listings.")
            continue

        # 4. Run Analysis
        print(f"Calculating analysis for {len(analysis_products)} products...")
        results = calculate_transient_upload_analysis(
            client_id=account_id,
            products=analysis_products,
            competitor_records=competitors
        )
        
        # 5. Save Results
        for p in analysis_products:
            save_pricing_analysis(p["asin"], "UAE", results)
            
    print("[SUCCESS] Force analysis complete!")

if __name__ == "__main__":
    force_analysis()
