print("Initializing SADDL Scraper Pipeline... (Loading dependencies, this can take 10-20 seconds)")
import os
import sys
import time
from datetime import datetime, date, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient

# Ensure we can import features
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import get_supabase_client
from features.price_benchmarking.apify_client import parse_apify_item
from features.price_benchmarking.relevance_filter import filter_related_products
from features.price_benchmarking.discovery_service import save_competitor_data, save_pricing_analysis, _clear_parent_dashboard_rows
from features.price_benchmarking.snapshot_service import calculate_transient_upload_analysis
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_account_prices, fetch_account_performance

load_dotenv()

def run_insulated_cups_mugs_scrape():
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        print("[ERROR] APIFY_TOKEN not found in environment variables or .env file.")
        return

    sb = get_supabase_client()
    account_id = "s2c_test"
    marketplace = "KSA"
    category_id = "22959836031" # Insulated Cups & Mugs category ID in Amazon.sa
    category_name = "Insulated Cups & Mugs"

    print("\n==================================================")
    print("   SADDL SCRAPER: INSULATED CUPS & MUGS PIPELINE  ")
    print("==================================================")

    # 1. Register s2c_org and s2c_test client in Supabase pb_clients so it appears in the UI
    print("\n[Step 1/7] Ensuring organization and client registration in Supabase (KSA)...")
    try:
        # Create unique organization s2c_org to bypass (org_id, marketplace) constraint
        sb.table("pb_organizations").upsert({
            "org_id": "s2c_org",
            "name": "s2c"
        }, on_conflict="org_id").execute()
        
        sb.table("pb_clients").upsert({
            "client_id": account_id,
            "name": "s2c_test",
            "marketplace": marketplace,
            "org_id": "s2c_org",
            "is_active": True
        }, on_conflict="client_id").execute()
        print("[OK] Client 's2c_test' successfully registered/updated under 's2c_org' for KSA.")
    except Exception as e:
        print(f"[WARNING] Error during client registration: {e}")

    # 2. Fetch the catalog products for s2c_test from SADDL
    print(f"\n[Step 2/7] Fetching SADDL catalog products for account '{account_id}'...")
    products = fetch_account_products_with_categories(account_id)
    # Filter products specifically for the Insulated Cups & Mugs category
    target_products = [p for p in products if str(p.get("category_id")) == category_id]
    
    if not target_products:
        print(f"[ERROR] No products found for category '{category_name}' (ID: {category_id}) under s2c_test.")
        return
        
    print(f"[OK] Found {len(target_products)} target variations in '{category_name}' category:")
    for p in target_products:
        print(f"   - ASIN: {p['asin']} | Parent ASIN: {p['parent_asin']} | Title: {p['title'][:40]}...")

    # Load child variation prices
    live_prices = fetch_account_prices(account_id)
    
    # Pre-onboard listings in pb_client_listings so pricing analysis has baseline prices
    print("\n[Step 3/7] Onboarding listings in pb_client_listings...")
    own_asins = set()
    parent_asin_map = {} # parent_asin -> list of child products
    for p in target_products:
        asin = p["asin"]
        parent_asin = p["parent_asin"]
        own_asins.add(asin)
        
        parent_asin_map.setdefault(parent_asin, []).append(p)
        
        # Get selling price or fallback
        listing_price = live_prices.get(asin) or 89.0
        try:
            sb.table("pb_client_listings").upsert({
                "client_id": account_id,
                "marketplace": marketplace,
                "asin": asin,
                "sku_id": asin,
                "listing_price": float(listing_price),
                "currency": "SAR",
                "strategy": "mid",
                "reference_name": ""
            }, on_conflict="client_id,asin").execute()
        except Exception as e:
            print(f"[WARNING] Listing onboard warning for ASIN {asin}: {e}")
    print(f"[OK] Successfully prepared {len(own_asins)} variation listings.")

    # 3. Trigger live Amazon category search scrape on Apify (KSA)
    print(f"\n[Step 4/7] Triggering live Apify category scrape on Amazon.sa for '{category_name}'...")
    apify_client = ApifyClient(apify_token)
    
    run_input = {
        "categoryOrProductUrls": [{"url": "https://www.amazon.sa/s?k=Insulated+Cups+Mugs"}],
        "maxItems": 50, # Set to 50 for temporary testing
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
            "apifyProxyCountry": "SA"
        },
        "locationCode": "sa"
    }

    try:
        run = apify_client.actor("junglee/amazon-crawler").call(run_input=run_input)
        print(f"[OK] Apify actor run succeeded! Status: {run['status']}")
        dataset_id = run["defaultDatasetId"]
        raw_items = apify_client.dataset(dataset_id).list_items().items
        print(f"[OK] Downloaded {len(raw_items)} raw product pages from Apify dataset: {dataset_id}")
    except Exception as e:
        print(f"[ERROR] Error executing Apify actor: {e}")
        return

    # 4. Parse crawled products & insert into raw events (pb_price_events)
    print("\n[Step 5/7] Parsing scraped items and writing raw historical price events...")
    
    # Ensure category is registered in pb_categories
    try:
        sb.table("pb_categories").upsert({
            "id": int(category_id),
            "keepa_cat_id": int(category_id),
            "marketplace": marketplace,
            "name": category_name
        }, on_conflict="id").execute()
    except Exception as e:
        print(f"[WARNING] Category register warning: {e}")

    parsed_competitors = []
    event_rows = []
    category_competitor_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    valid_db_keys = [
        "asin", "marketplace", "event_type", "floor_price", "ceiling_price", 
        "median_price", "mean_price", "n_offers", "buy_box_price", 
        "buy_box_is_fba", "foep", "competitive_price", "offers_json", 
        "created_at", "seller_name", "is_buy_box_winner", "shipping_price", 
        "category_name", "rating", "reviews", "sales_rank", "brand"
    ]
    
    for item in raw_items:
        parsed = parse_apify_item(item, marketplace)
        asin = parsed.get("asin")
        price = parsed.get("floor_price")
        
        if asin and price is not None:
            # Exclude our own ASINs from competitor analysis
            if asin in own_asins:
                continue
                
            parsed["category_name"] = category_name
            parsed["category_id"] = category_id
            parsed["created_at"] = now_iso
            
            # Prepare row for pb_category_competitors
            category_competitor_rows.append({
                "category_id": int(category_id),
                "marketplace": marketplace,
                "asin": asin,
                "title": parsed.get("title") or asin,
                "brand": parsed.get("brand") or "Generic",
                "source": "keepa_bsr",
                "is_active": True
            })
            
            # Clean parsed object to contain only exact columns of pb_price_events to prevent PG schema cache mismatches
            clean_parsed = {k: parsed[k] for k in valid_db_keys if k in parsed}
            clean_parsed["category_name"] = category_name
            clean_parsed["created_at"] = now_iso
            
            # For raw logging
            event_rows.append(clean_parsed)
            # For active competitor analysis
            parsed_competitors.append(parsed)

    if category_competitor_rows:
        try:
            sb.table("pb_category_competitors").upsert(category_competitor_rows, on_conflict="category_id,asin").execute()
            print(f"[OK] Successfully saved {len(category_competitor_rows)} canonical competitors into pb_category_competitors.")
        except Exception as e:
            print(f"[WARNING] Warning saving canonical competitors: {e}")

    if event_rows:
        try:
            sb.table("pb_price_events").insert(event_rows).execute()
            print(f"[OK] Successfully saved {len(event_rows)} raw price events into pb_price_events.")
        except Exception as e:
            print(f"[WARNING] Warning saving raw events: {e}")
    else:
        print("[ERROR] No valid competitor prices found in scrape results.")
        return

    # 5. Process discovery results and calculate pricing recommendations grouped by Parent ASIN
    print("\n[Step 6/7] Applying relevance filters and recomputing benchmarking recommendations...")
    
    for parent_asin, child_products in parent_asin_map.items():
        # Get baseline listing details
        representative_product = child_products[0]
        
        # Load reference name if saved in listings
        ref_name = ""
        try:
            listings_resp = sb.table("pb_client_listings").select("reference_name").eq("client_id", account_id).eq("asin", parent_asin).execute()
            if listings_resp.data:
                ref_name = listings_resp.data[0].get("reference_name") or ""
        except:
            pass
            
        representative_product["reference_name"] = ref_name
        representative_product["category_id"] = category_id
        
        # Apply Relevance Filter
        filtered_competitors = filter_related_products(
            target_product=representative_product,
            candidate_products=parsed_competitors,
            exclude_asins=own_asins
        )
        
        print(f"\n[INFO] Parent ASIN group: {parent_asin}")
        print(f"   Matches {len(filtered_competitors)} relevant competitor cups & mugs (Reference Keyword: '{ref_name or 'Unfiltered Category'}')")
        
        if not filtered_competitors:
            print("   [WARNING] Skipping parent group: No relevant competitors matched.")
            continue
            
        # Save competitor products mapping
        save_competitor_data(
            parent_asin=parent_asin,
            marketplace=marketplace,
            competitors=filtered_competitors,
            product_asins=[p["asin"] for p in child_products]
        )
        print("   [OK] Persisted filtered competitor products.")

        # Build analysis product input structure
        child_asins = [p["asin"] for p in child_products]
        child_prices = [float(live_prices.get(asin) or 89.0) for asin in child_asins]
        avg_listing_price = round(sum(child_prices) / len(child_prices), 2)
        
        analysis_input = [{
            "asin": parent_asin,
            "sku_id": parent_asin,
            "price": avg_listing_price,
            "marketplace": marketplace,
            "category_id": category_id,
            "category_ids": [category_id],
            "strategy": "mid",
            "min_price": None,
            "max_price": None,
            "parent_asin": parent_asin,
            "reference_name": ref_name,
            "title": representative_product.get("title") or parent_asin,
            "representative_child_asin": child_asins[0]
        }]
        
        # Compute Benchmarking Snapshots
        try:
            # Clear old stale dashboard rows first to avoid overlaps
            _clear_parent_dashboard_rows(sb, client_id=account_id, parent_asin=parent_asin, child_asins=child_asins, marketplace=marketplace)
            
            results = calculate_transient_upload_analysis(
                client_id=account_id,
                products=analysis_input,
                competitor_records=filtered_competitors
            )
            results["client_id"] = account_id
            
            # Save snapshots and recommendations to Supabase
            save_pricing_analysis(parent_asin, marketplace, results)
            print("   [OK] Repricing analysis calculated and saved.")
            
            # Get recommended price
            rec = results.get("recommendations", [{}])[0]
            snap = results.get("snapshots", [{}])[0]
            print(f"   [RESULT] Current Avg={avg_listing_price} SAR | Recommended={rec.get('recommended_price')} SAR ({rec.get('action')})")
            print(f"   [RESULT] Benchmark Range: Floor={snap.get('floor_price')} SAR | Median={snap.get('median_price')} SAR | Ceiling={snap.get('ceiling_price')} SAR | Position Percentile={snap.get('percentile_rank')}%")
            
        except Exception as e:
            print(f"   [ERROR] Error computing benchmarking snapshots: {e}")

    # 6. Mock daily performance details so the Audit tab is immediately populated
    print("\n[Step 7/7] Seeding historical performance details for s2c_test...")
    perf_rows = []
    today = date.today()
    for p in target_products:
        asin = p["asin"]
        for i in range(14): # Seed 14 days
            perf_date = (today - date.resolution * i).isoformat()
            perf_rows.append({
                "client_id": account_id,
                "asin": asin,
                "marketplace": marketplace,
                "performance_date": perf_date,
                "units_ordered": 25 - i,
                "sessions": 600 - (i * 20),
                "acos": 12.0 + (i * 0.4),
                "cvr": 0.045
            })
            
    try:
        # Clear existing performance and seed fresh
        sb.table("pb_client_performance_daily").delete().eq("client_id", account_id).execute()
        sb.table("pb_client_performance_daily").insert(perf_rows).execute()
        print("[OK] Seeding performance logs for Audit tab complete.")
    except Exception as e:
        print(f"[WARNING] Performance seeding warning: {e}")

    print("\n==================================================")
    print("  [SUCCESS] PIPELINE RUN COMPLETE: Insulated Cups & Mugs Scraped!")
    print("==================================================")
    print("Open http://127.0.0.1:8000/benchmarking in your browser, select 's2c_test' from the dropdown and enjoy the fresh data!")

if __name__ == "__main__":
    run_insulated_cups_mugs_scrape()
