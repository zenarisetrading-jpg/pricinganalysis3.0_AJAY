import os
from dotenv import load_dotenv
from features.price_benchmarking.discovery_service import save_pricing_analysis
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis
from features.price_benchmarking.saddl_db import (
    fetch_account_products_with_categories,
    execute_saddl_query
)
from db import get_supabase_client

def force_recalculate(account_id):
    load_dotenv()
    sb = get_supabase_client()
    
    print(f"Starting force re-calculation for {account_id}...")
    
    # 1. Fetch products
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        print("No products found.")
        return

    # 2. Group by category
    unique_categories = {}
    for p in products_data:
        cat_id = p["category_id"]
        if not cat_id: continue
        unique_categories.setdefault(cat_id, []).append(p)

    # 3. For each category, get competitors and re-analyze each product
    for cat_id, cat_products in unique_categories.items():
        print(f"\nRe-analyzing category {cat_id}...")
        
        # Get ALL competitors in this category from DB
        resp = sb.table("competitor_products").select("*").eq("category_id", cat_id).execute()
        competitors = resp.data or []
        print(f"  Found {len(competitors)} competitors in category.")

        # Group by Parent ASIN to avoid redundant calculations
        seen_parents = set()
        for p in cat_products:
            parent_asin = p["parent_asin"]
            if parent_asin in seen_parents: continue
            seen_parents.add(parent_asin)
            
            print(f"  - Analyzing Parent ASIN {parent_asin}...")
            
            # Get current listing price
            listing_resp = sb.table("pb_client_listings").select("*").eq("asin", parent_asin).eq("client_id", account_id).execute()
            if not listing_resp.data:
                print(f"    No listing price found for {parent_asin}, skipping.")
                continue
            
            l = listing_resp.data[0]
            p_title = p.get('title') or parent_asin
            print(f"    Product Title: {p_title}")

            # Fetch performance data for today's entry
            perf_query = """
            SELECT units_ordered, sessions, unit_session_percentage as cvr 
            FROM sc_raw.sales_traffic 
            WHERE child_asin = %s AND account_id = %s 
            ORDER BY report_date DESC LIMIT 1
            """
            perf_resp = execute_saddl_query(perf_query, (parent_asin, account_id))
            # [units, sessions, cvr] -> We need [units, sessions, acos, cvr]
            if perf_resp:
                r = perf_resp[0]
                perf = [r[0], r[1], 0, r[2]] # Setting ACOS to 0
            else:
                perf = [0, 0, 0, 0]

            # Prepare product for analysis
            price_val = l.get("listing_price")
            if price_val is None:
                price_val = p.get("price") or 50.0 # safety fallback
            analysis_products = [{
                "asin": parent_asin,
                "sku_id": parent_asin,
                "price": float(price_val),
                "marketplace": "UAE",
                "category_id": cat_id,
                "strategy": l.get("strategy") or "mid",
                "title": p_title,
                "min_price": l.get("min_price"),
                "max_price": l.get("max_price"),
                "units_ordered": perf[0],
                "sessions": perf[1],
                "acos": perf[2],
                "cvr": perf[3]
            }]
            
            # RUN THE ANALYSIS
            results = calculate_transient_upload_analysis(
                client_id=account_id,
                products=analysis_products,
                competitor_records=competitors
            )
            
            if not results.get("snapshots"):
                print(f"    DEBUG: No snapshots returned. Competitor sample (Full keys of first item):")
                if competitors:
                    print(f"      {competitors[0]}")
            
            # SAVE RESULTS
            save_pricing_analysis(parent_asin, "UAE", results)
            
            # Print the new reasoning/median to verify
            rec = next((r for r in results.get("recommendations", []) if r["asin"] == parent_asin), None)
            if rec:
                print(f"    DONE: Median {results['snapshots'][0]['median_price']} | Target {rec['recommended_price']} | Reasoning: {rec['reasoning'][:50]}...")

    print("\nForce re-calculation complete.")

if __name__ == "__main__":
    force_recalculate("oneshot_uae")
