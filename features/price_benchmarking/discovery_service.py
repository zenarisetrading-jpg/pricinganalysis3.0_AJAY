import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from db import get_supabase_client
from .saddl_db import fetch_account_products_with_categories, fetch_parent_asin_categories, fetch_account_prices, fetch_account_performance
from .apify_client import trigger_category_discovery, parse_apify_item
from .snapshot_service import calculate_transient_upload_analysis
from .relevance_filter import filter_related_products

MARKETPLACE_MAP = {
    "A2VIGQ35RCS4UG": {"domain": "amazon.ae", "name": "UAE"},
    "A17E79C6D8DWNP": {"domain": "amazon.sa", "name": "KSA"},
}

def get_cached_analysis(asin: str, marketplace: str):
    """Fetch recent analysis from the database."""
    sb = get_supabase_client()
    # Consider "fresh" if updated within the last 24 hours
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    resp = sb.table("pricing_analysis").select("*").eq("asin", asin).eq("marketplace", marketplace).gt("updated_at", yesterday).execute()
    return resp.data[0] if resp.data else None

def save_competitor_data(
    parent_asin: str,
    marketplace: str,
    competitors: List[Dict],
    product_asins: List[str] | None = None,
):
    """Persist raw competitor details."""
    sb = get_supabase_client()
    grouped_product_asins = sorted({asin for asin in (product_asins or [parent_asin]) if asin})
    rows = []
    for c in competitors:
        competitor_asin = c.get("asin")
        if not competitor_asin:
            continue
        rows.append({
            "parent_asin": parent_asin,
            "product_asins": grouped_product_asins,
            "competitor_asin": competitor_asin,
            "competitor_parent_asin": c.get("parent_asin"),
            "category_id": c.get("category_id"),
            "competitor_title": c.get("title"),
            "competitor_price": c.get("floor_price") or c.get("price") or c.get("competitor_price"),
            "rating": c.get("rating"),
            "reviews": c.get("reviews"),
            "rank": c.get("sales_rank"),
            "brand": c.get("brand"),
            "product_url": c.get("url"),
            "marketplace": marketplace,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "relevance_score": c.get("relevance_score", 1.0)
        })
    # Delete existing competitor records for this parent_asin to ensure only active, filtered competitors remain.
    sb.table("competitor_products").delete().eq("parent_asin", parent_asin).eq("marketplace", marketplace).execute()
    
    if rows:
        sb.table("competitor_products").insert(rows).execute()


def _clear_parent_dashboard_rows(
    sb,
    *,
    client_id: str,
    parent_asin: str,
    child_asins: List[str] | None,
    marketplace: str,
) -> None:
    """Remove stale dashboard rows for a parent group before saving fresh analysis."""
    identifiers = sorted({asin for asin in [parent_asin, *(child_asins or [])] if asin})

    sb.table("pb_recommendations").delete().eq("client_id", client_id).eq("parent_asin", parent_asin).eq("marketplace", marketplace).execute()
    sb.table("pb_alerts").delete().eq("client_id", client_id).eq("parent_asin", parent_asin).eq("marketplace", marketplace).execute()

    for asin in identifiers:
        sb.table("pb_recommendations").delete().eq("client_id", client_id).eq("asin", asin).eq("marketplace", marketplace).execute()
        sb.table("pb_alerts").delete().eq("client_id", client_id).eq("asin", asin).eq("marketplace", marketplace).execute()


def save_pricing_analysis(asin: str, marketplace: str, results: Dict):
    """Persist pricing analysis summary."""
    sb = get_supabase_client()
    
    # Map from transient results to our new table structure
    # Results from calculate_transient_upload_analysis snapshots
    # Find the snapshot for THIS asin (parent)
    snap = next((s for s in results.get("snapshots", []) if s["asin"] == asin), None)
    if not snap and results.get("snapshots"):
        # If no snapshot matches parent_asin, pick the first child as representative
        snap = results["snapshots"][0]
        
    if not snap:
        print(f"WARNING: No snapshot found for ASIN {asin}. Proceeding with defaults.")
        snap = {} # Fallback
        
    payload = {
        "asin": asin,
        "marketplace": marketplace,
        "lowest_price": snap.get("floor_price"),
        "highest_price": snap.get("ceiling_price"),
        "average_price": snap.get("average_price"),
        "median_price": snap.get("median_price"),
        "recommended_price": None,
        "premium_price": snap.get("p75_price"),
        "value_price": snap.get("p25_price"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Get recommendation for this ASIN
    rec = next((r for r in results.get("recommendations", []) if r["asin"] == asin), None)
    if not rec and results.get("recommendations"):
        rec = results["recommendations"][0]
    if rec:
        payload["recommended_price"] = rec.get("recommended_price")

    # Save to pricing_analysis table
    sb.table("pricing_analysis").upsert(payload, on_conflict="asin,marketplace").execute()

    account_id = results.get("client_id") or "oneshot_uae"
    child_asins = [
        row.get("asin")
        for row in [*results.get("snapshots", []), *results.get("recommendations", [])]
        if row.get("asin")
    ]

    # NEW: Centrally save performance data for the Audit tab
    if results.get("performance"):
        try:
            # results["performance"] is a list from snapshot_service
            perf_list = results.get("performance", [])
            for perf_item in perf_list:
                # Use delete-then-insert as a robust upsert
                sb.table("pb_client_performance_daily").delete().match({
                    "client_id": account_id,
                    "asin": perf_item["asin"],
                    "performance_date": perf_item["performance_date"]
                }).execute()
                
                # Clean the item to avoid PGRST204 schema errors
                clean_item = {k: v for k, v in perf_item.items() if k not in ["created_at", "updated_at"]}
                sb.table("pb_client_performance_daily").insert(clean_item).execute()
        except Exception as e:
            print(f"Warning: Failed to save performance data: {e}")

    # Also populate pb_client_snapshots_daily for the dashboard overview
    local_sb = get_supabase_client()
    
    snapshot_payload = {
        "client_id": account_id,
        "asin": asin,
        "sku_id": snap.get("sku_id") or asin, # Ensure sku_id is not null
        "parent_asin": asin, # Grouping key
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "your_price": snap.get("your_price"),
        "n_competitors": snap.get("n_competitors"),
        "floor_price": snap.get("floor_price"),
        "ceiling_price": snap.get("ceiling_price"),
        "median_price": snap.get("median_price"),
        "p25_price": snap.get("p25_price"),
        "p75_price": snap.get("p75_price"),
        "index_vs_median": snap.get("index_vs_median"),
        "zone": snap.get("zone"),
        "strategy": snap.get("strategy")
    }
    local_sb.table("pb_client_snapshots_daily").upsert(snapshot_payload, on_conflict="client_id,asin,snapshot_date").execute()

    # Clear old data specifically for THIS parent group only (not the whole account).
    _clear_parent_dashboard_rows(
        sb,
        client_id=account_id,
        parent_asin=asin,
        child_asins=child_asins,
        marketplace=marketplace,
    )

    # Also populate one canonical recommendation for the parent group.
    # Child-level recommendations are useful inside the calculation, but the
    # dashboard is parent-ASIN based and old child rows are cleared above.
    all_recs = results.get("recommendations", [])
    if all_recs:
        representative_rec = next((r for r in all_recs if r.get("asin") == asin), all_recs[0])
        representative_snap = next(
            (s for s in results.get("snapshots", []) if s.get("asin") == representative_rec.get("asin")),
            snap,
        ) or {}
        category_ids = sorted({
            str(category_id)
            for product in results.get("products", [])
            for category_id in (product.get("category_ids") or [product.get("category_id")])
            if category_id
        })
        metadata = dict(representative_rec.get("metadata") or representative_snap.get("metadata") or {})
        metadata.setdefault("n_competitors", representative_snap.get("n_competitors"))
        if category_ids:
            metadata["category_ids"] = category_ids
        if representative_rec.get("asin") and representative_rec.get("asin") != asin:
            metadata["representative_child_asin"] = representative_rec["asin"]

        row = {
            "client_id": account_id,
            "sku_id": representative_rec.get("sku_id") or representative_snap.get("sku_id") or asin,
            "asin": asin,
            "parent_asin": asin,
            "marketplace": marketplace,
            "strategy": representative_rec.get("strategy") or representative_snap.get("strategy") or "mid",
            "current_price": representative_rec.get("current_price") or representative_snap.get("your_price") or 0.0,
            "recommended_price": representative_rec.get("recommended_price") or 0.0,
            "action": representative_rec.get("action") or "neutral",
            "reasoning": representative_rec.get("reasoning") or "Analysis completed.",
            "metadata": metadata,
            "confidence": representative_rec.get("confidence") or "high",
            "status": "pending",
            "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            sb.table("pb_recommendations").insert(row).execute()
            print(f"Successfully saved parent recommendation for {asin}")
        except Exception as e:
            print(f"FAILED to save recommendation for {asin}: {str(e)}")

    # Also populate alerts for the dashboard
    alerts = results.get("alerts", [])
    asin_alerts = []
    for a in alerts:
        a_asin = getattr(a, 'asin', None) or (a.get('asin') if isinstance(a, dict) else None)
        if a_asin == asin or a_asin is None: # If None, assume it belongs to the current context
            asin_alerts.append(a)
    
    if asin_alerts:
        alert_rows = []
        for a in asin_alerts:
            # Handle object or dict
            is_obj = hasattr(a, 'alert_type')
            alert_rows.append({
                "client_id": account_id,
                "asin": asin,
                "parent_asin": asin,
                "sku_id": snap.get("sku_id") or asin,
                "marketplace": marketplace,
                "alert_type": a.alert_type.value if is_obj else (a.get("type") or "price_alert"),
                "severity": a.severity.value if is_obj else (a.get("severity") or "medium"),
                "title": a.title if is_obj else (a.get("title") or "Price Alert"),
                "message": a.message if is_obj else (a.get("message") or "Check product pricing vs competitors."),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        if alert_rows:
            sb.table("pb_alerts").insert(alert_rows).execute()

def _product_asins_for_parent(products_data: List[Dict[str, Any]], category_id: str, parent_asin: str) -> List[str]:
    return sorted({
        p["asin"]
        for p in products_data
        if str(p.get("category_id")) == str(category_id)
        and p.get("parent_asin") == parent_asin
        and p.get("asin")
    })


def _append_unique_category(categories: List[Dict[str, Any]], product: Dict[str, Any]) -> None:
    category_id = product.get("category_id")
    if not category_id:
        return
    if any(str(c.get("category_id")) == str(category_id) for c in categories):
        return
    categories.append({
        "category_id": category_id,
        "category_name": product.get("category_name"),
        "marketplace_id": product.get("marketplace_id"),
    })


def _build_parent_analysis_product(
    *,
    sb,
    account_id: str,
    parent_asin: str,
    parent_products: List[Dict[str, Any]],
    marketplace: str,
    category_ids: List[str],
    actual_prices: Dict[str, float],
    reference_name: str | None = None,
) -> Dict[str, Any]:
    """Build one canonical pricing input for a parent ASIN group."""
    child_asins = [p["asin"] for p in parent_products if p.get("asin")]
    listing_rows = []
    try:
        listing_resp = (
            sb.table("pb_client_listings")
            .select("*")
            .eq("client_id", account_id)
            .in_("asin", [*child_asins, parent_asin])
            .execute()
        )
        listing_rows = listing_resp.data or []
    except Exception as e:
        print(f"Warning: Failed to fetch listings for parent {parent_asin}: {e}")

    listing_by_asin = {row.get("asin"): row for row in listing_rows if row.get("asin")}
    representative_asins = [parent_asin, *child_asins]
    representative_listing = next(
        (
            listing_by_asin.get(asin)
            for asin in representative_asins
            if listing_by_asin.get(asin)
            and (listing_by_asin[asin].get("listing_price") or listing_by_asin[asin].get("price"))
        ),
        {},
    )
    representative_child = next(
        (
            asin
            for asin in representative_asins
            if (listing_by_asin.get(asin, {}).get("listing_price") or listing_by_asin.get(asin, {}).get("price") or actual_prices.get(asin))
        ),
        parent_asin,
    )
    # Calculate the average price of all active child variations
    child_prices = []
    for p in parent_products:
        c_asin = p.get("asin")
        if not c_asin:
            continue
        c_listing = listing_by_asin.get(c_asin, {})
        c_price = (
            c_listing.get("listing_price")
            or c_listing.get("price")
            or actual_prices.get(c_asin)
        )
        if c_price and float(c_price) > 0:
            child_prices.append(float(c_price))

    if child_prices:
        price = round(sum(child_prices) / len(child_prices), 2)
    else:
        price = (
            representative_listing.get("listing_price")
            or representative_listing.get("price")
            or actual_prices.get(representative_child)
            or 0.0
        )
    strategy = representative_listing.get("strategy") or "mid"
    if not reference_name:
        reference_name = next((row.get("reference_name") for row in listing_rows if row.get("reference_name")), None)
        
    exclude_keywords = next((row.get("exclude_keywords") for row in listing_rows if row.get("exclude_keywords")), None)

    first_product = parent_products[0] if parent_products else {}
    return {
        "asin": parent_asin,
        "sku_id": parent_asin,
        "price": price,
        "marketplace": marketplace,
        "category_id": category_ids[0] if category_ids else first_product.get("category_id"),
        "category_ids": category_ids,
        "strategy": strategy,
        "min_price": representative_listing.get("min_price"),
        "max_price": representative_listing.get("max_price"),
        "parent_asin": parent_asin,
        "reference_name": reference_name,
        "exclude_keywords": exclude_keywords,
        "title": first_product.get("title") or parent_asin,
        "representative_child_asin": representative_child,
    }


def trigger_background_discovery(account_id: str, force: bool = False):
    """
    Trigger the background scraping process.
    Refactored to be parent_asin-centric.
    """
    # 1. Fetch products and actual selling prices from SADDL
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        return {"status": "error", "message": f"No products found for account {account_id}"}
    
    # Pre-fetch actual prices and performance from sales traffic as a reliable fallback
    actual_prices = fetch_account_prices(account_id)
    live_performance = fetch_account_performance(account_id)
    
    sb = get_supabase_client()
    
    # Resolve marketplace from pb_clients configuration to handle mismatched SADDL catalog marketplace_ids
    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace from pb_clients: {e}")

    if client_marketplace == "KSA":
        mp_info = {"domain": "amazon.sa", "name": "KSA"}
    else:
        mp_info = {"domain": "amazon.ae", "name": "UAE"}

    
    # 2. Group products by parent_asin and collect their categories
    parent_asin_map = {} # parent_asin -> {products: [], categories: []}
    all_unique_categories = {} # category_id -> {marketplace_id: str, name: str}
    
    for p in products_data:
        parent_asin = p["parent_asin"]
        if not parent_asin: continue
        
        if parent_asin not in parent_asin_map:
            # Get ALL categories for this parent_asin (it might belong to multiple)
            categories = fetch_parent_asin_categories(account_id, parent_asin)
            parent_asin_map[parent_asin] = {
                "products": [],
                "categories": categories,
                "marketplace_id": p["marketplace_id"]
            }
            for cat in categories:
                all_unique_categories[cat["category_id"]] = {
                    "marketplace_id": cat["marketplace_id"],
                    "name": cat["category_name"]
                }
        
        parent_asin_map[parent_asin]["products"].append(p)
        _append_unique_category(parent_asin_map[parent_asin]["categories"], p)
        if p.get("category_id"):
            all_unique_categories[p["category_id"]] = {
                "marketplace_id": p.get("marketplace_id"),
                "name": p.get("category_name"),
            }

    print(f"Processing {len(parent_asin_map)} parent ASINs across {len(all_unique_categories)} unique categories...")
    
    # 3. Scrape all unique categories and store results
    category_results = {} # category_id -> List[parsed_items]
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    sb = get_supabase_client()
    
    triggered_categories = []
    skipped_categories = []
    errors = []

    # Check if we are in a local environment
    app_url = os.environ.get("APP_URL")
    is_local = not app_url or "localhost" in app_url or "127.0.0.1" in app_url

    def scrape_category(cat_id, cat_info):
        marketplace_id = cat_info["marketplace_id"]
        mp_info = MARKETPLACE_MAP.get(marketplace_id)
        if not mp_info:
            return cat_id, None, f"Marketplace {marketplace_id} not supported."

        if not force:
            resp = sb.table("competitor_products").select("*").eq("category_id", cat_id).gt("scraped_at", yesterday).execute()
            if resp.data:
                return cat_id, resp.data, "cached"

        try:
            run_id, dataset_id = trigger_category_discovery(
                category_url=f"https://{mp_info['domain']}/s?node={cat_id}",
                marketplace=mp_info["name"],
                category_id=cat_id,
                account_id=account_id,
                max_items=1000 # Increased to get a larger pool
            )
            
            if is_local:
                from .apify_client import poll_for_results
                items = poll_for_results(run_id)
                parsed_items = []
                for item in items:
                    parsed = parse_apify_item(item, mp_info["name"])
                    parsed["category_id"] = cat_id
                    parsed_items.append(parsed)
                return cat_id, parsed_items, "scraped"
            else:
                return cat_id, [], "triggered" # In production, webhooks handle this
        except Exception as e:
            return cat_id, None, str(e)

    # STEP 3: Discovery (DISABLED - Manual Scrapes Only)
    print("Auto-discovery disabled. Using existing data in competitor_products table.")
    # (Removed ThreadPoolExecutor block)

    # 4. For each parent_asin, merge results from its categories, filter, and analyze
    for parent_asin, data in parent_asin_map.items():
        # Category-first comparison:
        # - Single-category parents compare against that category only.
        # - Multi-category parents merge all categories for that parent, then analyze as one parent group.
        cats = data["categories"]
        cat_ids = [c["category_id"] for c in cats]
        
        merged_competitors = []
        seen_asins = {}
        
        for cid in cat_ids:
            cat_pool = fetch_competitors_by_category(cid, mp_info["name"])
            for item in cat_pool:
                _merge_competitor(merged_competitors, seen_asins, item)
        
        pool_label = "merged category pool" if len(cat_ids) > 1 else "category pool"
        print(f"Parent {parent_asin}: {pool_label} size: {len(merged_competitors)} (Categories: {len(cat_ids)})")
        
        if not merged_competitors:
            print(f"No competitors found in the database for parent {parent_asin}")
            continue

        # Get target product metadata for filtering
        target_product = data["products"][0]
        
        # Fetch the parent keyword from any child listing in this parent group.
        # The Categories tab saves the same reference_name to every child ASIN.
        child_asins = [p["asin"] for p in data["products"]]
        listing_resp = sb.table("pb_client_listings").select("reference_name, exclude_keywords").in_("asin", [*child_asins, parent_asin]).execute()
        
        # We might get multiple rows, pick the first one that has a reference_name or exclude_keywords
        for row in listing_resp.data or []:
            if row.get("reference_name"):
                target_product["reference_name"] = row["reference_name"]
            if row.get("exclude_keywords"):
                target_product["exclude_keywords"] = row["exclude_keywords"]
            if row.get("reference_name") or row.get("exclude_keywords"):
                break
        
        # Apply Relevance Filtering
        own_asins = {p["asin"] for p in products_data if p.get("asin")}
        filtered_competitors = filter_related_products(target_product, merged_competitors, exclude_asins=own_asins)
        print(f"Parent ASIN {parent_asin}: Filtered {len(merged_competitors)} -> {len(filtered_competitors)} relevant competitors. Reference Name used: {target_product.get('reference_name')}")

        # Save merged/filtered competitor data
        save_competitor_data(
            parent_asin=parent_asin,
            marketplace=mp_info["name"],
            competitors=filtered_competitors,
            product_asins=[p["asin"] for p in data["products"]],
        )

        # Prepare one canonical parent-level analysis product.
        analysis_products = [
            _build_parent_analysis_product(
                sb=sb,
                account_id=account_id,
                parent_asin=parent_asin,
                parent_products=data["products"],
                marketplace=mp_info["name"],
                category_ids=cat_ids,
                actual_prices=actual_prices,
                reference_name=target_product.get("reference_name"),
            )
        ]

        if analysis_products:
            try:
                results = calculate_transient_upload_analysis(
                    client_id=account_id,
                    products=analysis_products,
                    competitor_records=filtered_competitors
                )
                results["client_id"] = account_id
                print(f"CRITICAL: Saving analysis for parent {parent_asin} with {len(results.get('recommendations', []))} recommendations.")
                save_pricing_analysis(parent_asin, mp_info["name"], results)
                
                # Save performance data
                if live_performance:
                    # Filter performance for the children being processed in this parent group
                    child_asins = {p["asin"] for p in data["products"]}
                    relevant_perf = [p for p in live_performance if p["asin"] in child_asins]
                    
                    if relevant_perf:
                        for p_row in relevant_perf:
                            # Clean for DB to match Supabase schema
                            db_row = {
                                "client_id": account_id,
                                "asin": p_row["asin"],
                                "performance_date": p_row["performance_date"],
                                "units_ordered": p_row["units_ordered"],
                                "sessions": p_row["sessions"],
                                "cvr": p_row["cvr"],
                                "marketplace": "UAE" # Default
                            }
                            sb.table("pb_client_performance_daily").upsert(
                                db_row,
                                on_conflict="client_id,asin,marketplace,performance_date"
                            ).execute()




            except Exception as e:
                print(f"ERROR analyzing parent {parent_asin}: {str(e)}")
                import traceback
                traceback.print_exc()

    return {
        "status": "completed",
        "parent_asin_count": len(parent_asin_map),
        "triggered_categories": triggered_categories,
        "skipped_categories": skipped_categories,
        "errors": errors,
        "message": f"Processed {len(parent_asin_map)} parent ASINs. Scraped {len(triggered_categories)} categories, skipped {len(skipped_categories)}."
    }

def recalculate_parent_from_categories(account_id: str, parent_asin: str) -> Dict[str, Any]:
    """Recalculate one parent ASIN using only its linked category_id competitor pools."""
    products_data = fetch_account_products_with_categories(account_id)
    parent_products = [p for p in products_data if p.get("parent_asin") == parent_asin or p.get("asin") == parent_asin]
    if not parent_products:
        return {"status": "error", "message": f"No products found for parent_asin {parent_asin}"}

    sb = get_supabase_client()
    actual_prices = fetch_account_prices(account_id)

    # Resolve marketplace from pb_clients configuration to handle mismatched SADDL catalog marketplace_ids
    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace from pb_clients: {e}")

    if client_marketplace == "KSA":
        mp_info = {"domain": "amazon.sa", "name": "KSA"}
    else:
        mp_info = {"domain": "amazon.ae", "name": "UAE"}

    cats = fetch_parent_asin_categories(account_id, parent_asin)
    for product in parent_products:
        _append_unique_category(cats, product)
    cat_ids = [c["category_id"] for c in cats]
    merged_competitors = []
    seen_asins = {}

    for cid in cat_ids:
        for item in fetch_competitors_by_category(cid, mp_info["name"]):
            _merge_competitor(merged_competitors, seen_asins, item)

    child_asins = [p["asin"] for p in parent_products]

    if not merged_competitors:
        _clear_parent_dashboard_rows(
            sb,
            client_id=account_id,
            parent_asin=parent_asin,
            child_asins=child_asins,
            marketplace=mp_info["name"],
        )
        return {
            "status": "no_competitors",
            "parent_asin": parent_asin,
            "category_ids": cat_ids,
            "message": "No competitors found for linked categories",
        }

    target_product = parent_products[0].copy()
    listing_resp = sb.table("pb_client_listings").select("reference_name, exclude_keywords").eq("client_id", account_id).in_("asin", [*child_asins, parent_asin]).execute()
    for row in listing_resp.data or []:
        if row.get("reference_name"):
            target_product["reference_name"] = row["reference_name"]
        if row.get("exclude_keywords"):
            target_product["exclude_keywords"] = row["exclude_keywords"]
        if row.get("reference_name") or row.get("exclude_keywords"):
            break

    own_asins = {p["asin"] for p in products_data if p.get("asin")}
    filtered_competitors = filter_related_products(target_product, merged_competitors, exclude_asins=own_asins)
    save_competitor_data(
        parent_asin=parent_asin,
        marketplace=mp_info["name"],
        competitors=filtered_competitors,
        product_asins=child_asins,
    )

    analysis_products = [
        _build_parent_analysis_product(
            sb=sb,
            account_id=account_id,
            parent_asin=parent_asin,
            parent_products=parent_products,
            marketplace=mp_info["name"],
            category_ids=cat_ids,
            actual_prices=actual_prices,
            reference_name=target_product.get("reference_name"),
        )
    ]

    results = calculate_transient_upload_analysis(
        client_id=account_id,
        products=analysis_products,
        competitor_records=filtered_competitors,
    )
    results["client_id"] = account_id
    save_pricing_analysis(parent_asin, mp_info["name"], results)

    snapshots = results.get("snapshots") or []
    representative = next((s for s in snapshots if s.get("asin") == parent_asin), snapshots[0] if snapshots else {})
    return {
        "status": "success",
        "parent_asin": parent_asin,
        "category_ids": cat_ids,
        "keyword": target_product.get("reference_name") or "",
        "category_competitors": len(merged_competitors),
        "filtered_competitors": len(filtered_competitors),
        "priced_competitors": representative.get("n_competitors", 0),
        "message": f"Recalculated {parent_asin} from {len(cat_ids)} category_id pool(s).",
    }

def fetch_all_from_supabase(table_name: str, filters: Dict[str, Any]) -> List[Dict]:
    """Helper to fetch all rows with pagination to bypass the 1000 row limit."""
    sb = get_supabase_client()
    all_rows = []
    offset = 0
    page_size = 1000
    
    while True:
        query = sb.table(table_name).select("*").range(offset, offset + page_size - 1)
        for key, value in filters.items():
            query = query.eq(key, value)
        
        resp = query.execute()
        if not resp.data:
            break
            
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
        
    return all_rows

def fetch_competitors_by_category(category_id: str, marketplace: str) -> List[Dict]:
    """Fetch the full competitor pool stored for a category."""
    category_pool = _fetch_category_competitor_price_pool(category_id, marketplace)

    rows = fetch_all_from_supabase("competitor_products", {
        "category_id": category_id,
        "marketplace": marketplace
    })

    # If the pool is completely empty in the requested marketplace, try fallback to "UAE"
    if not category_pool and not rows and marketplace != "UAE":
        print(f"INFO: Mapped competitor pool for category {category_id} is empty in marketplace {marketplace}. Falling back to UAE pool.")
        category_pool = _fetch_category_competitor_price_pool(category_id, "UAE")
        rows = fetch_all_from_supabase("competitor_products", {
            "category_id": category_id,
            "marketplace": "UAE"
        })

    # Normalize keys for analysis (asin, price, title)
    legacy_pool = [{
        "asin": r["competitor_asin"],
        "floor_price": r["competitor_price"],
        "price": r["competitor_price"],
        "title": r["competitor_title"],
        "brand": r["brand"],
        "parent_asin": r.get("competitor_parent_asin"),
        "category_id": r.get("category_id"),
        "rating": r.get("rating"),
        "reviews": r.get("reviews"),
    } for r in rows]

    merged = []
    seen_asins = {}
    for item in [*category_pool, *legacy_pool]:
        _merge_competitor(merged, seen_asins, item)
    return merged


def _fetch_category_competitor_price_pool(category_id: str, marketplace: str) -> List[Dict]:
    """
    Build the category-level pool from canonical category competitors and latest prices.

    competitor_products stores parent-specific analysis output as well as legacy
    category rows, so it can be narrowed by an earlier keyword run. This source is
    independent of a parent ASIN and should be preferred for no-keyword analysis.
    """
    sb = get_supabase_client()
    try:
        competitor_rows = fetch_all_from_supabase("pb_category_competitors", {
            "category_id": category_id,
            "marketplace": marketplace,
            "is_active": True,
        })
    except Exception as e:
        print(f"Warning: Failed to fetch category competitors for {category_id}: {e}")
        return []

    asin_rows = [row for row in competitor_rows if row.get("asin")]
    if not asin_rows:
        return []

    latest_prices: Dict[str, Any] = {}
    asin_set = {row["asin"] for row in asin_rows}
    try:
        price_resp = (
            sb.table("pb_price_events")
            .select("asin, floor_price, buy_box_price, median_price, competitive_price, rating, reviews, brand, created_at")
            .eq("marketplace", marketplace)
            .in_("asin", list(asin_set))
            .order("created_at", desc=True)
            .execute()
        )
        for row in price_resp.data or []:
            asin = row.get("asin")
            if asin and asin not in latest_prices:
                latest_prices[asin] = {
                    "price": (
                        row.get("floor_price")
                        or row.get("buy_box_price")
                        or row.get("median_price")
                        or row.get("competitive_price")
                    ),
                    "rating": row.get("rating"),
                    "reviews": row.get("reviews"),
                    "brand": row.get("brand")
                }
    except Exception as e:
        print(f"Warning: Failed to fetch latest category prices for {category_id}: {e}")
        return []

    pool = []
    for row in asin_rows:
        price_data = latest_prices.get(row["asin"])
        if not price_data or price_data.get("price") in (None, "", 0):
            continue
        pool.append({
            "asin": row["asin"],
            "floor_price": price_data["price"],
            "price": price_data["price"],
            "title": row.get("title") or row["asin"],
            "brand": row.get("brand") or price_data.get("brand"),
            "parent_asin": None,
            "category_id": str(category_id),
            "source": "category_competitors",
            "rating": price_data.get("rating"),
            "reviews": price_data.get("reviews"),
        })

    return pool

def fetch_competitors_for_parent(parent_asin: str, marketplace: str) -> List[Dict]:
    """Fetch all competitors stored for a parent ASIN group."""
    rows = fetch_all_from_supabase("competitor_products", {
        "parent_asin": parent_asin,
        "marketplace": marketplace
    })
    return [{
        "asin": r["competitor_asin"],
        "floor_price": r["competitor_price"],
        "price": r["competitor_price"],
        "title": r["competitor_title"],
        "brand": r["brand"],
        "parent_asin": r.get("competitor_parent_asin"),
        "category_id": r.get("category_id"),
        "rating": r.get("rating"),
        "reviews": r.get("reviews"),
    } for r in rows]

def _merge_competitor(merged_competitors: List[Dict], seen_asins: Dict[str, int], item: Dict) -> None:
    """Deduplicate by competitor ASIN, preferring rows that have usable prices."""
    asin = item.get("asin")
    if not asin:
        return

    existing_index = seen_asins.get(asin)
    if existing_index is None:
        seen_asins[asin] = len(merged_competitors)
        merged_competitors.append(item)
        return

    existing = merged_competitors[existing_index]
    existing_price = existing.get("floor_price") or existing.get("price") or existing.get("competitor_price")
    new_price = item.get("floor_price") or item.get("price") or item.get("competitor_price")

    if (existing_price is None or existing_price == 0) and new_price not in (None, 0):
        merged_competitors[existing_index] = item
    elif new_price not in (None, 0):
        for key in ("floor_price", "price", "competitor_price", "category_id", "title", "brand", "parent_asin", "rating", "reviews"):
            if existing.get(key) in (None, "") and item.get(key) not in (None, ""):
                existing[key] = item[key]

def run_competitor_analysis_workflow(account_id: str):
    """
    Unified entry point for the discovery workflow.
    Tries to return cached analysis first, otherwise triggers background scrape.
    """
    # 1. Fetch products to check for their cached analysis
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        return {"status": "error", "message": "No products found"}
        
    sb = get_supabase_client()
    
    # Resolve marketplace from pb_clients configuration to handle mismatched SADDL catalog marketplace_ids
    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace from pb_clients: {e}")

    if client_marketplace == "KSA":
        mp_info = {"domain": "amazon.sa", "name": "KSA"}
    else:
        mp_info = {"domain": "amazon.ae", "name": "UAE"}

    # Check if we have analysis for the first few Parent ASINs
    results = []
    seen_parents = set()
    for p in products_data:
        parent_asin = p["parent_asin"]
        if parent_asin in seen_parents: continue
        seen_parents.add(parent_asin)
        
        cached = get_cached_analysis(parent_asin, mp_info["name"])
        if cached:
            results.append(cached)
        
        if len(results) >= 5: break # Sample size
            
    if results:
        return {
            "status": "ok",
            "source": "database",
            "results": results
        }
        
    # If no cached results, trigger background discovery
    trigger_status = trigger_background_discovery(account_id)
    return {
        "status": "processing",
        "message": "Analysis not found or stale. Background scraping triggered.",
        "details": trigger_status
    }
