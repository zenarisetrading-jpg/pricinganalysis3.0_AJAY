"""
Standalone FastAPI routes for the price benchmarking module.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from auth import get_current_client_id
from db import get_supabase_client

from .apify_client import fetch_dataset_results, parse_apify_item, trigger_price_scrape, trigger_category_discovery, trigger_search_discovery
from .nightly import aggregate_daily, purge_old_events
from .snapshot_service import calculate_benchmarks_for_client, calculate_transient_upload_analysis, _resolve_majority_categories

from .saddl_db import fetch_saddl_accounts, fetch_saddl_categories
from .discovery_service import run_competitor_analysis_workflow


def _load_account_parent_map(client_id: str) -> tuple[Dict[str, str], set[str]]:
    """Return child ASIN -> parent ASIN and the allowed parent ASIN set for an account."""
    from .saddl_db import fetch_account_products_with_categories

    products = fetch_account_products_with_categories(client_id)
    child_to_parent = {
        product["asin"]: product["parent_asin"]
        for product in products
        if product.get("asin") and product.get("parent_asin")
    }
    parent_asins = {parent for parent in child_to_parent.values() if parent}
    return child_to_parent, parent_asins


def ensure_client_exists(supabase, client_id: str, name: str | None = None) -> str:
    """Ensure the client_id is present in pb_clients table."""
    check = supabase.table("pb_clients").select("client_id, marketplace").eq("client_id", client_id).execute()
    if check.data:
        return check.data[0]["marketplace"] or "UAE"
    
    # Not found, let's find the marketplace
    from .saddl_db import fetch_account_products_with_categories
    from .discovery_service import MARKETPLACE_MAP
    
    marketplace = "UAE"
    products = fetch_account_products_with_categories(client_id)
    if products:
        m_id = products[0].get("marketplace_id")
        marketplace = MARKETPLACE_MAP.get(m_id, {"name": "UAE"})["name"]
        
    # Dynamically insert/upsert parent organization to satisfy foreign key constraint
    org_id = f"{client_id}_org"
    supabase.table("pb_organizations").upsert({
        "org_id": org_id,
        "name": f"{client_id.replace('_', ' ').title()} Org",
        "type": "seller"
    }).execute()

    supabase.table("pb_clients").upsert({
        "client_id": client_id,
        "name": name or client_id.replace('_', ' ').title(),
        "marketplace": marketplace,
        "org_id": org_id,
        "is_active": True
    }).execute()
    
    return marketplace


def is_automation_enabled(supabase) -> bool:
    """Helper to check if automation is globally enabled."""
    try:
        resp = supabase.table("pb_settings").select("value").eq("key", "automation_enabled").execute()
        if resp.data:
            return resp.data[0]["value"] is True
    except Exception as e:
        # If table doesn't exist, assume enabled by default
        print(f"WARNING: Settings table not found: {e}")
    return True

router = APIRouter()


async def verify_client_access(
    client_id: str | None = Query(None),
    current_client_id: str = Depends(get_current_client_id),
):
    """
    Ensure the requester has access to the client.
    In v2, this should eventually check the pb_clients / pb_organizations tables.
    For now, it relies on the auth.py's simplistic client_id check.
    """
    if client_id is None:
        return None
    if current_client_id != client_id and current_client_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this client's data")
    return client_id


async def require_internal_token(x_internal_token: str | None = Header(None, alias="X-Internal-Token")):
    expected = os.getenv("INTERNAL_TOKEN")
    if not expected:
        # If not configured, deny all internal triggers for safety
        raise HTTPException(status_code=500, detail="Internal token not configured")
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token")


@router.post("/webhook/apify")
async def handle_apify_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase_client)
):
    """
    Receives webhook from Apify when a scrape job completes.
    Parses the data and stores it in pb_price_events (Tier 1).
    If it's a discovery scrape, it also seeds pb_category_competitors.
    """
    # Extract dataset ID and metadata from webhook payload
    resource = payload.get("resource", {})
    meta = payload.get("meta", {})
    dataset_id = resource.get("defaultDatasetId")
    
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Missing dataset ID in webhook payload")
    
    # Fetch results from Apify dataset
    items = fetch_dataset_results(dataset_id)
    
    if not items:
        return {"status": "success", "processed": 0, "message": "Empty dataset"}
    
    # Determine marketplace
    marketplace = meta.get("marketplace")
    if not marketplace:
        first_url = items[0].get("url", "")
        marketplace = "UAE" if ".ae" in first_url else "KSA"
    
    # Parse and prepare for bulk insert
    event_rows = []
    competitor_rows = []
    skipped_count = 0
    
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    
    for item in items:
        parsed = parse_apify_item(item, marketplace)
        asin = parsed.get("asin")
        price = parsed.get("floor_price")
        
        if asin and price is not None:
            parsed["created_at"] = now_iso
            cat_name = parsed.get("category_name", "Unknown")
            if "recorded_at" in parsed:
                del parsed["recorded_at"]
            parsed.pop("parent_asin", None)
            parsed.pop("url", None)
            parsed.pop("title", None)
            event_rows.append(parsed)
            
            # If discovery, prepare competitor entries
            if meta.get("type") == "discovery_scrape":
                cat_id = meta.get("category_id")
                if cat_id:
                    competitor_rows.append({
                        "category_id": cat_id,
                        "marketplace": marketplace,
                        "asin": asin,
                        "title": item.get("title") or item.get("name"),
                        "brand": item.get("brand"),
                        "source": "apify_search",
                        "is_active": True,
                        "added_at": now_iso,
                        "updated_at": now_iso
                    })
        else:
            skipped_count += 1
            if not asin:
                print(f"[Skip] No ASIN found for item starting with {str(item)[:50]}...")
            elif price is None:
                print(f"[Skip] ASIN {asin}: No price found in any field.")
            
    print(f"[Webhook] {len(event_rows)} saved, {skipped_count} skipped")
    
    # Bulk insert into Tier 1 (Price Events)
    if event_rows:
        try:
            supabase.table("pb_price_events").insert(event_rows).execute()
        except Exception as e:
            print(f"[ERROR] DATABASE ERROR (Price Events): {e}")
            raise
        
    # If discovery, seed competitors table
    if competitor_rows:
        try:
            supabase.table("pb_category_competitors").upsert(
                competitor_rows, 
                on_conflict="category_id,asin"
            ).execute()
        except Exception as e:
            print(f"Warning: Failed to upsert competitors: {e}")

    # NEW: Handle discovery_scrape specifically for the new database-driven architecture
    if meta.get("type") == "discovery_scrape":
        account_id = meta.get("account_id")
        if account_id:
            # We want to run a transient analysis for this account and save it
            # 1. Save raw competitor data to the new table
            # We use the results of parse_apify_item which we already have in event_rows (slightly different structure)
            # Actually, I'll pass event_rows to save_competitor_data
            # But event_rows has 'floor_price', 'buy_box_price', etc. 
            # while save_competitor_data expects the parsed dict.
            background_tasks.add_task(process_discovery_results, account_id, marketplace, event_rows, meta.get("category_id"))
    
    # Trigger benchmark calculation in background
    background_tasks.add_task(calculate_benchmarks_for_marketplace, marketplace, supabase)
    
    return {
        "status": "success",
        "processed": len(event_rows),
        "competitors_added": len(competitor_rows),
        "marketplace": marketplace,
        "dataset_id": dataset_id,
        "type": meta.get("type")
    }


async def process_discovery_results(account_id: str, marketplace: str, event_rows: List[Dict], category_id: str):
    """Background task to save discovery data and compute initial analysis."""
    from .discovery_service import (
        fetch_account_products_with_categories, 
        save_competitor_data, 
        save_pricing_analysis
    )
    from .snapshot_service import calculate_transient_upload_analysis
    from .relevance_filter import filter_related_products
    from db import get_supabase_client
    
    # 1. Normalize raw competitor products
    for r in event_rows:
        r["category_id"] = category_id
        # Ensure 'title' exists for save_competitor_data
        if "title" not in r:
            r["title"] = r.get("asin")
    
    # 2. Trigger analysis for this account, grouped by parent ASIN
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        return
        
    supabase = get_supabase_client()
    parent_groups = {}
    for p in products_data:
        # Filter by category if possible
        if category_id and str(p.get("category_id")) != str(category_id):
            continue
            
        listing = supabase.table("pb_client_listings").select("*").eq("asin", p["asin"]).execute()
        if listing.data:
            l = listing.data[0]
            parent_asin = p["parent_asin"]
            parent_groups.setdefault(parent_asin, []).append({
                "asin": p["asin"],
                "sku_id": p["asin"],
                "price": l["listing_price"],
                "marketplace": marketplace,
                "category_id": p["category_id"],
                "strategy": l.get("strategy") or "mid",
                "min_price": l.get("min_price"),
                "max_price": l.get("max_price"),
                "reference_name": l.get("reference_name"),
                "title": p.get("title")
            })

    for parent_asin, analysis_products in parent_groups.items():
        # Get representative target product
        target_product = analysis_products[0]
        
        # Apply Relevance Filtering
        own_asins = {p["asin"] for p in products_data if p.get("asin")}
        filtered_competitors = filter_related_products(target_product, event_rows, exclude_asins=own_asins)
        
        save_competitor_data(
            parent_asin=parent_asin,
            marketplace=marketplace,
            competitors=filtered_competitors,
            product_asins=[p["asin"] for p in analysis_products],
        )

        results = calculate_transient_upload_analysis(
            client_id=account_id,
            products=analysis_products,
            competitor_records=filtered_competitors
        )
        save_pricing_analysis(parent_asin, marketplace, results)


def calculate_benchmarks_for_marketplace(marketplace: str, supabase):
    """
    Background task: Calculate benchmarks for all active clients in a marketplace.
    """
    from .snapshot_service import calculate_benchmarks_for_client
    
    clients_resp = supabase.table("pb_clients")\
        .select("client_id")\
        .eq("marketplace", marketplace)\
        .eq("is_active", True)\
        .execute()
    
    for client in (clients_resp.data or []):
        calculate_benchmarks_for_client(
            supabase=supabase,
            client_id=client["client_id"],
            marketplace=marketplace
        )


@router.post("/trigger-scrape")
async def trigger_scrape_route(
    marketplace: str,
    asins: list[str] | None = None,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client)
):
    """
    Manually trigger an Apify scrape for specific ASINs or all tracked competitors.
    """
    # Check if automation is enabled
    if not is_automation_enabled(supabase):
        return {
            "status": "skipped",
            "message": "Scraping automation is currently disabled."
        }

    # If no ASINs provided, get all active competitors for this marketplace
    if not asins:
        competitors_resp = supabase.table("pb_category_competitors")\
            .select("asin")\
            .eq("marketplace", marketplace)\
            .eq("is_active", True)\
            .execute()
        
        asins = [r["asin"] for r in (competitors_resp.data or [])]
    
    if not asins:
        raise HTTPException(status_code=404, detail=f"No ASINs found for {marketplace}")
    
    # Trigger the scrape (returns dataset ID)
    dataset_id = trigger_price_scrape(asins, marketplace)
    
    return {
        "status": "scrape_triggered",
        "marketplace": marketplace,
        "asin_count": len(asins),
        "dataset_id": dataset_id,
        "message": "Results will be POSTed to /webhook/apify when ready"
    }


@router.post("/discover-competitors")
async def discover_competitors_route(
    category_url: str,
    marketplace: str,
    category_id: int,
    max_items: int = 100,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client)
):
    """
    Scrapes a category page to find new competitor ASINs.
    Seeds pb_category_competitors table.
    """
    # Trigger the scrape
    run_id, dataset_id = trigger_category_discovery(category_url, marketplace, category_id, max_items)
    
    # In production, we'd use a webhook for this too, but for discovery
    # we'll fetch results (this might need a delay or polling in a real script)
    # For now, return the dataset_id and let the user fetch later or use the webhook
    
    return {
        "status": "discovery_triggered",
        "marketplace": marketplace,
        "dataset_id": dataset_id,
        "message": "Check Apify dataset when finished"
    }




class CreateClientRequest(BaseModel):
    client_id: str
    name: str
    marketplace: str
    org_id: str
    sp_api_profile_id: str | None = None


class SnapshotRequest(BaseModel):
    client_id: str
    marketplace: str


class UpsertListingRequest(BaseModel):
    client_id: str
    marketplace: str
    asin: str
    sku_id: str
    listing_price: float
    currency: str


class OnboardProductsRequest(BaseModel):
    client_id: str
    marketplace: str
    products: list[dict] # {asin, sku_id, listing_price, currency}


class UpdateReferenceNameRequest(BaseModel):
    client_id: str
    parent_asin: str
    reference_name: str
    exclude_keywords: str | None = None


class CategoryScrapeRequest(BaseModel):
    category_name: str
    marketplace: str
    max_items: int = 100


class UploadPriceRecord(BaseModel):
    asin: str
    marketplace: str
    floor_price: float | None = None
    buy_box_price: float | None = None
    seller_name: str | None = "Manual Upload"
    is_buy_box_winner: bool = False
    shipping_price: float = 0.0
    category_name: str | None = "Uploaded"
    category_id: str | None = None
    title: str | None = None
    sales_rank: float | None = None
    bsr_rank: float | None = None
    rank: float | None = None


class UploadDataRequest(BaseModel):
    records: list[UploadPriceRecord]
    persist: bool = True
    client_id: str | None = None
    products: list[dict[str, Any]] | None = None


@router.get("/accounts")
async def list_accounts():
    """List all Amazon accounts available for benchmarking from external SADDL DB."""
    accounts = fetch_saddl_accounts()
    return {"accounts": accounts}


@router.get("/account-bsr-categories")
async def get_account_bsr_categories(
    account_id: str = Query(...),
    supabase=Depends(get_supabase_client),
):
    """
    Fetch unique BSR categories for the selected account from external SADDL DB.
    Also attach reference names from pb_client_listings.
    """
    ensure_client_exists(supabase, account_id)
    categories = fetch_saddl_categories(account_id)
    
    # Fetch all listings to map reference_name and exclude_keywords
    resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords").eq("client_id", account_id).execute()
    listings = resp.data or []
    ref_map = {l["asin"]: l.get("reference_name") or "" for l in listings}
    
    # Fetch saddl_products to get child -> parent mapping and resolve dominant category
    from .saddl_db import fetch_account_products_with_categories
    saddl_products = fetch_account_products_with_categories(account_id)
    saddl_products = _resolve_majority_categories(saddl_products)
    
    child_to_parent = {p["asin"]: p["parent_asin"] for p in saddl_products}
    
    # Map parent_asin -> resolved category_name
    parent_to_resolved_category = {}
    for p in saddl_products:
        parent = p.get("parent_asin")
        cat_name = p.get("category_name")
        if parent and cat_name:
            parent_to_resolved_category[parent.strip()] = cat_name.strip()
            
    # Filter the categories list so each parent_asin is mapped to exactly one category
    filtered_categories = []
    for c in categories:
        c_name_norm = c["category_name"].strip().lower()
        filtered_products = []
        for p in c.get("products", []):
            parent = p.get("asin")  # In fetch_saddl_categories, the product dict has 'asin' representing parent_asin
            if parent:
                resolved_cat = parent_to_resolved_category.get(parent.strip())
                if resolved_cat and resolved_cat.strip().lower() == c_name_norm:
                    filtered_products.append(p)
                elif not resolved_cat:
                    filtered_products.append(p)
            else:
                filtered_products.append(p)
                
        if filtered_products:
            c["products"] = filtered_products
            c["asin_count"] = len(filtered_products)
            ranks = [prod["rank"] for prod in filtered_products if prod.get("rank") is not None]
            c["avg_rank"] = sum(ranks) / len(ranks) if ranks else 0.0
            filtered_categories.append(c)
            
    categories = filtered_categories

    # Map parent_asin & child_asin -> reference_name and exclude_keywords
    parent_ref_map = {}
    parent_exclude_map = {}
    for l in listings:
        p_asin = child_to_parent.get(l["asin"], l["asin"])
        if l.get("reference_name"):
            parent_ref_map[p_asin] = l["reference_name"]
            parent_ref_map[l["asin"]] = l["reference_name"]
        if l.get("exclude_keywords"):
            parent_exclude_map[p_asin] = l["exclude_keywords"]
            parent_exclude_map[l["asin"]] = l["exclude_keywords"]
            
    # Also collect categories per ASIN (both parent and child for variation robustness)
    asin_categories = {}
    for p in saddl_products:
        cat = p.get("category_name")
        if cat:
            asin_categories.setdefault(p["asin"], set()).add(cat)
            asin_categories.setdefault(p["parent_asin"], set()).add(cat)

    for c in categories:
        for p in c.get("products", []):
            product_cats = asin_categories.get(p["asin"]) or set()
            p["category_name"] = ", ".join(sorted(list(product_cats)))
            p["reference_name"] = parent_ref_map.get(p["asin"], "")
            p["exclude_keywords"] = parent_exclude_map.get(p["asin"], "")
            
    return {"categories": categories}

@router.post("/trigger-category-scrape")
async def trigger_category_scrape_route(
    body: CategoryScrapeRequest,
    _token: None = Depends(require_internal_token),
):
    """
    Trigger an Apify scrape for a specific BSR category name.
    """
    try:
        dataset_id = trigger_search_discovery(
            query=body.category_name,
            marketplace=body.marketplace,
            max_items=body.max_items
        )
        
        return {
            "status": "triggered",
            "dataset_id": dataset_id,
            "category": body.category_name,
            "message": "Apify search initiated. Results will be processed via webhook."
        }
    except Exception as e:
        import traceback
        print(f"[ERROR] in trigger_category_scrape_route: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-competitor-analysis")
async def trigger_competitor_analysis_route(
    account_id: str = Query(...),
    background_tasks: BackgroundTasks = None,
    _token: None = Depends(require_internal_token),
):
    """
    Triggers the full competitor discovery and pricing analysis workflow.
    Uses database-driven architecture: returns cached results if fresh,
    otherwise triggers background scraping.
    """
    try:
        # Returns results instantly from DB if fresh, otherwise triggers background scrape
        results = run_competitor_analysis_workflow(account_id)
        return results
    except Exception as e:
        import traceback
        print(f"[ERROR] in trigger_competitor_analysis_route: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/clients", status_code=201)
async def create_client(
    body: CreateClientRequest,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client),
):
    resp = supabase.table("pb_clients").upsert(body.model_dump()).execute()
    return {"client": (resp.data or [None])[0]}


@router.get("/listings")
async def list_listings(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    resp = supabase.table("pb_client_listings").select("*").eq("client_id", client_id).execute()
    return {"listings": resp.data or []}


@router.post("/listings", status_code=201)
async def upsert_listing(
    body: UpsertListingRequest,
    current_client_id: str = Depends(get_current_client_id),
    supabase=Depends(get_supabase_client),
):
    # Manual access check since client_id is in body
    if current_client_id != body.client_id and current_client_id != "admin":
         raise HTTPException(status_code=403, detail="Access denied")
         
    resp = supabase.table("pb_client_listings").upsert(body.model_dump()).execute()
    return {"listing": (resp.data or [None])[0]}




@router.post("/run-snapshot")
async def run_snapshot(
    body: SnapshotRequest,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client),
):
    """
    Triggers a manual snapshot run via Apify.
    Replaces the old synchronous SP-API logic.
    """
    if not body.client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    from .apify_client import trigger_price_scrape
    
    # Trigger the scrape (returns dataset ID)
    # We scrape all active competitors for the client's marketplace
    dataset_id = trigger_price_scrape([], body.marketplace) # Passing empty list will trigger discovery-based scrape in client
    # Wait, trigger_price_scrape expects a list of ASINs. 
    # I should fetch them here.
    
    competitors_resp = supabase.table("pb_category_competitors")\
        .select("asin")\
        .eq("marketplace", body.marketplace)\
        .eq("is_active", True)\
        .execute()
    
    asins = [r["asin"] for r in (competitors_resp.data or [])]
    
    if not asins:
         raise HTTPException(status_code=404, detail="No competitors found to scrape")
         
    dataset_id = trigger_price_scrape(asins, body.marketplace)

    return {
        "status": "triggered",
        "dataset_id": dataset_id,
        "message": "Apify scrape initiated. Results will be processed via webhook."
    }


@router.post("/nightly")
async def run_nightly(
    target_date: str | None = Query(default=None),
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client),
):
    parsed_date = date.fromisoformat(target_date) if target_date else None
    aggregation = aggregate_daily(supabase, parsed_date)
    purge = purge_old_events(supabase)
    return {"aggregation": aggregation, "purge": purge}


@router.get("/overview")
async def get_overview(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    ensure_client_exists(supabase, client_id)
    resp = (
        supabase.table("pb_client_snapshots_daily")
        .select("*")
        .eq("client_id", client_id)
        .order("snapshot_date", desc=True)
        .execute()
    )
    rows = resp.data or []

    child_to_parent: Dict[str, str] = {}
    parent_asins: set[str] = set()
    parent_titles_map: Dict[str, str] = {}
    parent_ref_map: Dict[str, str] = {}
    parent_asin_count = 0
    try:
        # 1. Fetch parent_asin mapping from SADDL DB
        from .saddl_db import fetch_account_products_with_categories, fetch_saddl_categories
        saddl_products = fetch_account_products_with_categories(client_id)
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }
        parent_titles_map = {
            p["parent_asin"]: p["title"]
            for p in saddl_products
            if p.get("parent_asin") and p.get("title")
        }
        
        # Calculate total parent ASINs across all categories to match Categories table
        categories = fetch_saddl_categories(client_id)
        
        # Apply majority category resolution and filter categories to get exact unique parent ASIN count
        saddl_products = _resolve_majority_categories(saddl_products)
        parent_to_resolved_category = {}
        for p in saddl_products:
            parent = p.get("parent_asin")
            cat_name = p.get("category_name")
            if parent and cat_name:
                parent_to_resolved_category[parent.strip()] = cat_name.strip()
                
        filtered_categories = []
        for c in categories:
            c_name_norm = c["category_name"].strip().lower()
            filtered_products = []
            for p in c.get("products", []):
                parent = p.get("asin")
                if parent:
                    resolved_cat = parent_to_resolved_category.get(parent.strip())
                    if resolved_cat and resolved_cat.strip().lower() == c_name_norm:
                        filtered_products.append(p)
                    elif not resolved_cat:
                        filtered_products.append(p)
                else:
                    filtered_products.append(p)
            if filtered_products:
                c["products"] = filtered_products
                c["asin_count"] = len(filtered_products)
                filtered_categories.append(c)
                
        parent_asin_count = sum([c["asin_count"] for c in filtered_categories])
        
        # Load reference names and exclude keywords from Supabase
        listings_resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords").eq("client_id", client_id).execute()
        listings = listings_resp.data or []
        parent_exclude_map = {}
        for l in listings:
            asin = l.get("asin")
            ref_name = l.get("reference_name")
            exclude_keywords = l.get("exclude_keywords")
            p_asin = child_to_parent.get(asin, asin)
            if asin and ref_name:
                parent_ref_map[p_asin] = ref_name
            if asin and exclude_keywords:
                parent_exclude_map[p_asin] = exclude_keywords
    except Exception as e:
        print(f"Warning: Failed to fetch parent ASIN mapping/titles/ref names for overview: {e}")

    snapshot_rows = _latest_snapshots_by_parent(rows, child_to_parent)

    # Filter snapshot rows to only BSR-categorized parent ASINs so the product selector
    # dropdown and Tracked Parent ASINs KPI are consistent (both show the same 16).
    if filtered_categories:
        _bsr_snaps: set[str] = set()
        for _c in filtered_categories:
            for _p in _c.get("products", []):
                _pa = _p.get("asin")
                if _pa:
                    _bsr_snaps.add(_pa.strip())
        if _bsr_snaps:
            snapshot_rows = [
                r for r in snapshot_rows
                if (r.get("parent_asin") or r.get("asin")) in _bsr_snaps
            ]

    # Query latest rating/reviews for our own ASINs in get_overview
    asin_list = [r["asin"] for r in snapshot_rows if r.get("asin")]
    rating_map = {}
    reviews_map = {}
    if asin_list:
        try:
            price_events = supabase.table("pb_price_events")\
                .select("asin, rating, reviews")\
                .in_("asin", asin_list)\
                .order("created_at", desc=True)\
                .execute()
            for pe in (price_events.data or []):
                asin = pe["asin"]
                if asin not in rating_map and pe.get("rating") is not None:
                    rating_map[asin] = float(pe["rating"])
                    reviews_map[asin] = int(pe["reviews"]) if pe.get("reviews") is not None else 0
        except Exception as pe_err:
            print(f"Warning: Failed to load own ratings for overview: {pe_err}")

    for r in snapshot_rows:
        parent_asin = r.get("parent_asin") or r.get("asin")
        r["title"] = parent_titles_map.get(parent_asin) or ""
        r["reference_name"] = parent_ref_map.get(parent_asin) or ""
        r["exclude_keywords"] = parent_exclude_map.get(parent_asin) or ""
        r["rating"] = rating_map.get(r.get("asin")) or rating_map.get(parent_asin)
        r["reviews"] = reviews_map.get(r.get("asin")) or reviews_map.get(parent_asin)

    return {
        "rows": snapshot_rows,
        "parent_asin_count": parent_asin_count if parent_asin_count > 0 else None,
    }



@router.get("/alerts")
async def get_alerts(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    resp = (
        supabase.table("pb_alerts")
        .select("*")
        .eq("client_id", client_id)
        .eq("is_resolved", False)
        .order("created_at", desc=True)
        .execute()
    )
    alerts = resp.data or []

    child_to_parent: Dict[str, str] = {}
    parent_titles_map: Dict[str, str] = {}
    try:
        from .saddl_db import fetch_account_products_with_categories
        saddl_products = fetch_account_products_with_categories(client_id)

        # Build child -> parent mapping
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }

        # Build parent_asin -> title mapping
        for p in saddl_products:
            p_asin = p.get("parent_asin") or p.get("asin")
            title = p.get("title")
            if p_asin and title and title != p_asin:
                if p_asin not in parent_titles_map or len(title) > len(parent_titles_map[p_asin]):
                    parent_titles_map[p_asin] = title
    except Exception as e:
        print(f"Warning: Failed to fetch parent ASIN/titles for alerts: {e}")

    for a in alerts:
        asin = a.get("asin")
        parent_asin = a.get("parent_asin") or child_to_parent.get(asin) or asin
        a["parent_asin"] = parent_asin
        a["parent_title"] = parent_titles_map.get(parent_asin) or ""

    return {"alerts": alerts}


def _latest_recommendations_by_parent(
    recommendations: List[Dict[str, Any]],
    child_to_parent: Dict[str, str] | None = None,
    allowed_parent_asins: set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Keep the newest pending recommendation for each current-account parent group."""
    child_to_parent = child_to_parent or {}
    allowed_parent_asins = allowed_parent_asins or set()

    def sort_key(row: Dict[str, Any]) -> tuple[str, str, int]:
        is_parent_row = int(bool(row.get("parent_asin")) and row.get("asin") == row.get("parent_asin"))
        return (
            str(row.get("created_at") or ""),
            str(row.get("snapshot_date") or ""),
            is_parent_row,
        )

    latest: dict[str, Dict[str, Any]] = {}
    for row in recommendations:
        asin = row.get("asin")
        key = child_to_parent.get(asin) or row.get("parent_asin") or asin
        if not key:
            continue

        if allowed_parent_asins and key not in allowed_parent_asins:
            continue

        normalized = dict(row)
        normalized["parent_asin"] = key
        if normalized.get("asin") != key:
            if not isinstance(normalized.get("metadata"), dict):
                normalized["metadata"] = {}
            normalized["metadata"].setdefault("representative_child_asin", normalized.get("asin"))
            normalized["asin"] = key

        existing = latest.get(key)
        if existing is None or sort_key(normalized) > sort_key(existing):
            latest[key] = normalized

    return sorted(latest.values(), key=sort_key, reverse=True)


def _latest_snapshots_by_parent(
    snapshots: List[Dict[str, Any]],
    child_to_parent: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    """Keep the newest snapshot for each parent group and expose parent_asin consistently."""
    child_to_parent = child_to_parent or {}

    def sort_key(row: Dict[str, Any]) -> tuple[str, str, int]:
        is_parent_row = int(bool(row.get("parent_asin")) and row.get("asin") == row.get("parent_asin"))
        return (
            str(row.get("snapshot_date") or ""),
            str(row.get("created_at") or ""),
            is_parent_row,
        )

    latest: dict[str, Dict[str, Any]] = {}
    for row in snapshots:
        asin = row.get("asin")
        key = child_to_parent.get(asin) or row.get("parent_asin") or asin
        if not key:
            continue

        normalized = dict(row)
        normalized["parent_asin"] = key
        existing = latest.get(key)
        if existing is None or sort_key(normalized) > sort_key(existing):
            latest[key] = normalized

    return sorted(latest.values(), key=sort_key, reverse=True)


@router.get("/recommendations")
async def get_recommendations(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    ensure_client_exists(supabase, client_id)
    resp = (
        supabase.table("pb_recommendations")
        .select("*")
        .eq("client_id", client_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .order("snapshot_date", desc=True)
        .execute()
    )
    
    child_to_parent: Dict[str, str] = {}
    parent_asins: set[str] = set()
    try:
        child_to_parent, parent_asins = _load_account_parent_map(client_id)
    except Exception as e:
        print(f"Warning: Failed to fetch parent ASIN mapping for recommendations: {e}")

    recs = _latest_recommendations_by_parent(resp.data or [], child_to_parent, parent_asins)

    # Override current_price with the average of live variation prices directly from SADDL db
    from .saddl_db import fetch_account_prices, fetch_account_products_with_categories, fetch_saddl_categories
    parent_titles_map = {}
    parent_ref_map = {}
    try:
        live_prices = fetch_account_prices(client_id)
        saddl_products = fetch_account_products_with_categories(client_id)

        # Apply the same BSR-category filtering used by get_overview so that the
        # Pending Recs KPI counts only the same parent ASINs as Tracked Parent ASINs.
        # Parent ASINs that exist in SADDL but have no recent BSR rank data are excluded.
        _parent_to_resolved_cat: Dict[str, str] = {}  # init before try for safe scope
        try:
            _cats = fetch_saddl_categories(client_id)
            _resolved_products = _resolve_majority_categories(saddl_products)
            _parent_to_resolved_cat = {}
            for _p in _resolved_products:
                _pa = _p.get("parent_asin")
                _cn = _p.get("category_name")
                if _pa and _cn:
                    _parent_to_resolved_cat[_pa.strip()] = _cn.strip()

            _bsr_parent_asins: set[str] = set()
            for _c in _cats:
                _c_norm = _c["category_name"].strip().lower()
                for _p in _c.get("products", []):
                    _pa = _p.get("asin")
                    if _pa:
                        _resolved = _parent_to_resolved_cat.get(_pa.strip())
                        if (_resolved and _resolved.strip().lower() == _c_norm) or not _resolved:
                            _bsr_parent_asins.add(_pa.strip())

            if _bsr_parent_asins:
                recs = [r for r in recs if (r.get("parent_asin") or r.get("asin")) in _bsr_parent_asins]
        except Exception as _e:
            print(f"Warning: Failed to apply BSR category filter for recommendations: {_e}")
        
        # Build child -> parent mapping
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }
        
        # Build parent_asin -> title mapping
        for p in saddl_products:
            p_asin = p.get("parent_asin") or p.get("asin")
            title = p.get("title")
            if p_asin and title and title != p_asin:
                if p_asin not in parent_titles_map or len(title) > len(parent_titles_map[p_asin]):
                    parent_titles_map[p_asin] = title
                    
        # Load reference names and exclude keywords from Supabase
        listings_resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords").eq("client_id", client_id).execute()
        listings = listings_resp.data or []
        parent_exclude_map = {}
        for l in listings:
            asin = l.get("asin")
            ref_name = l.get("reference_name")
            exclude_keywords = l.get("exclude_keywords")
            p_asin = child_to_parent.get(asin, asin)
            if asin and ref_name:
                parent_ref_map[p_asin] = ref_name
            if asin and exclude_keywords:
                parent_exclude_map[p_asin] = exclude_keywords
        
        # Group live variation prices by their parent_asin
        parent_prices_map = {}
        for child_asin, price in live_prices.items():
            if price is not None and price > 0:
                p_asin = child_to_parent.get(child_asin, child_asin)
                parent_prices_map.setdefault(p_asin, []).append(float(price))
        
        # Override the current price with the calculated variation average
        for r in recs:
            parent_asin = r.get("parent_asin") or r.get("asin")
            variation_prices = parent_prices_map.get(parent_asin)
            
            if variation_prices:
                r["current_price"] = round(sum(variation_prices) / len(variation_prices), 2)
            else:
                # Fallback to single lookup if mapping details are not present
                metadata = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
                price_keys = [
                    r.get("asin"),
                    r.get("parent_asin"),
                    metadata.get("representative_child_asin"),
                ]
                for asin_key in price_keys:
                    if asin_key in live_prices:
                        r["current_price"] = live_prices[asin_key]
                        break
    except Exception as e:
        print(f"Warning: Failed to fetch live prices/titles/ref names for recommendations: {e}")
        
    for r in recs:
        parent_asin = r.get("parent_asin") or r.get("asin")
        r["title"] = parent_titles_map.get(parent_asin) or ""
        r["reference_name"] = parent_ref_map.get(parent_asin) or ""
        r["exclude_keywords"] = parent_exclude_map.get(parent_asin) or ""
        # Attach category_name so the frontend category dropdown can filter by it
        try:
            r["category_name"] = _parent_to_resolved_cat.get(parent_asin.strip(), "") if parent_asin else ""
        except Exception:
            r["category_name"] = ""

    # Enrich competitor metadata dynamically with ratings, reviews, and brands
    try:
        comp_asins = set()
        for r in recs:
            meta = r.get("metadata")
            if isinstance(meta, dict) and "competitors" in meta:
                for c in meta["competitors"]:
                    if isinstance(c, dict) and c.get("asin"):
                        comp_asins.add(c["asin"])
        
        if comp_asins:
            # Query competitor_products via sc_raw.competitor_pricing to get rating, reviews, and brand
            from .saddl_db import fetch_competitor_pricing_by_asins
            comp_data_rows = fetch_competitor_pricing_by_asins(list(comp_asins))
            
            comp_map = {}
            for row in comp_data_rows:
                casin = row["competitor_asin"]
                if casin not in comp_map:
                    comp_map[casin] = row
            
            # Query pb_price_events as fallback
            price_events_resp = supabase.table("pb_price_events")\
                .select("asin, rating, reviews, brand")\
                .in_("asin", list(comp_asins))\
                .order("created_at", desc=True)\
                .execute()
            for row in (price_events_resp.data or []):
                casin = row["asin"]
                if casin not in comp_map:
                    comp_map[casin] = {
                        "competitor_asin": casin,
                        "rating": row.get("rating"),
                        "reviews": row.get("reviews"),
                        "brand": row.get("brand")
                    }
                else:
                    existing = comp_map[casin]
                    if existing.get("rating") is None:
                        existing["rating"] = row.get("rating")
                    if existing.get("reviews") is None:
                        existing["reviews"] = row.get("reviews")
                    if existing.get("brand") is None:
                        existing["brand"] = row.get("brand")

            # Enrich competitor items in recs
            for r in recs:
                meta = r.get("metadata")
                if isinstance(meta, dict) and "competitors" in meta:
                    for c in meta["competitors"]:
                        if isinstance(c, dict) and c.get("asin"):
                            casin = c["asin"]
                            if casin in comp_map:
                                info = comp_map[casin]
                                if info.get("rating") is not None:
                                    c["rating"] = float(info["rating"])
                                if info.get("reviews") is not None:
                                    c["reviews"] = int(info["reviews"])
                                if info.get("brand") is not None:
                                    c["brand"] = info["brand"]
    except Exception as enrich_err:
        print(f"Warning: Failed to dynamically enrich competitor metadata: {enrich_err}")
        
    return {"recommendations": recs}


@router.get("/automation-status")
async def get_automation_status(supabase=Depends(get_supabase_client)):
    return {"enabled": is_automation_enabled(supabase)}


@router.post("/toggle-automation")
async def toggle_automation(
    enabled: bool,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client)
):
    supabase.table("pb_settings").upsert({
        "key": "automation_enabled",
        "value": enabled
    }).execute()
    return {"status": "ok", "enabled": enabled}


@router.post("/upload-data")
async def upload_data(
    body: UploadDataRequest,
    background_tasks: BackgroundTasks,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client)
):
    """
    Upload real/live competitor data manually.
    Triggers benchmark recalculation for the affected marketplaces.
    """
    if not body.records:
        return {"status": "success", "processed": 0}

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # IF PERSIST IS FALSE: Perform transient analysis and return results.
    # This path is intentionally isolated from Supabase reads/writes when the
    # caller provides the tested product catalog.
    if not body.persist:
        if not body.client_id:
             raise HTTPException(status_code=400, detail="client_id is required for transient analysis")

        if body.products is None:
            raise HTTPException(
                status_code=400,
                detail="Simulation mode requires uploaded product details. Upload your product JSON/CSV first while Save to DB is off.",
            )

        results = calculate_transient_upload_analysis(
            client_id=body.client_id,
            products=body.products,
            competitor_records=[rec.model_dump() for rec in body.records],
        )
        
        return {
            "status": "success",
            "mode": "simulation",
            "source": "uploaded_files_only",
            "results": results
        }

    # IF PERSIST IS TRUE: Save to DB as before
    event_rows = []
    marketplaces = set()
    
    for rec in body.records:
        row = rec.model_dump()
        # Fallback for floor_price
        if row.get("floor_price") is None:
            row["floor_price"] = row.get("buy_box_price")
        
        if row["floor_price"] is None:
            continue # Skip records with no price at all
            
        row["created_at"] = now_iso
        row["event_type"] = "poll" # Use 'poll' for now to match existing DB constraints
        event_rows.append(row)
        marketplaces.add(rec.marketplace)

    # Insert into Tier 1
    if event_rows:
        supabase.table("pb_price_events").insert(event_rows).execute()
        
    # Trigger benchmark calculation for each marketplace
    for mp in marketplaces:
        background_tasks.add_task(calculate_benchmarks_for_marketplace, mp, supabase)
        
    return {
        "status": "success",
        "processed": len(event_rows),
        "marketplaces": list(marketplaces)
    }


@router.post("/onboard-products")
async def onboard_products(
    body: OnboardProductsRequest,
    supabase=Depends(get_supabase_client)
):
    """
    Onboard the client's own product list.
    Populates pb_benchmarking_skus and pb_client_listings.
    """
    sku_rows = []
    listing_rows = []
    
    for p in body.products:
        asin = p.get("asin")
        sku = p.get("sku_id") or p.get("sku")
        price = p.get("listing_price") or p.get("price")
        curr = p.get("currency") or "AED"
        
        if not asin or not sku:
            continue
            
        sku_rows.append({
            "client_id": body.client_id,
            "asin": asin,
            "sku_id": sku,
            "marketplace": body.marketplace,
            "is_active": True
        })
        
        listing_rows.append({
            "client_id": body.client_id,
            "marketplace": body.marketplace,
            "asin": asin,
            "sku_id": sku,
            "listing_price": price,
            "currency": curr
        })

    if sku_rows:
        supabase.table("pb_benchmarking_skus").upsert(sku_rows, on_conflict="client_id,sku_id,marketplace").execute()
    if listing_rows:
        supabase.table("pb_client_listings").upsert(listing_rows, on_conflict="client_id,asin,marketplace").execute()
        
    return {
        "status": "success",
        "registered": len(sku_rows)
    }


@router.get("/client-listings")
async def get_client_listings(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    """Fetch all product listings for a client, grouped by parent ASIN."""
    # 1. Fetch all products from SADDL to get parent_asin mappings
    from .saddl_db import fetch_account_products_with_categories
    saddl_products = fetch_account_products_with_categories(client_id)
    
    asin_categories = {}
    for p in saddl_products:
        cat = p.get("category_name")
        if cat:
            asin_categories.setdefault(p["asin"], set()).add(cat)

    # 2. Fetch listings
    resp = (
        supabase.table("pb_client_listings")
        .select("*")
        .eq("client_id", client_id)
        .execute()
    )
    listings = resp.data or []
    
    # 3. Group by parent ASIN
    grouped = {}
    for l in listings:
        parent = parent_map.get(l["asin"], l["asin"]) # Fallback to child if no parent found
        if parent not in grouped:
            grouped[parent] = {
                "parent_asin": parent,
                "reference_name": l.get("reference_name") or "",
                "exclude_keywords": l.get("exclude_keywords") or "",
                "children": []
            }
        grouped[parent]["children"].append(l)
        
        # Keep the reference name consistent if we find one that's set
        if l.get("reference_name"):
            grouped[parent]["reference_name"] = l["reference_name"]
        if l.get("exclude_keywords"):
            grouped[parent]["exclude_keywords"] = l["exclude_keywords"]

    return {"grouped_listings": list(grouped.values())}


@router.post("/update-reference-name")
async def update_reference_name(
    body: UpdateReferenceNameRequest,
    background_tasks: BackgroundTasks,
    current_client_id: str = Depends(get_current_client_id),
    supabase=Depends(get_supabase_client),
):
    """Update the manual reference name for all products under a parent ASIN."""
    if current_client_id != body.client_id and current_client_id != "admin":
         raise HTTPException(status_code=403, detail="Access denied")

    ensure_client_exists(supabase, body.client_id)
    try:
        reference_name = body.reference_name.strip()
        from .saddl_db import fetch_account_products_with_categories
        from .discovery_service import MARKETPLACE_MAP, _clear_parent_dashboard_rows, recalculate_parent_from_categories
        saddl_products = fetch_account_products_with_categories(body.client_id)
        
        # Find all child ASINs for this parent
        child_asins = [
            p["asin"] for p in saddl_products 
            if p["parent_asin"] == body.parent_asin or p["asin"] == body.parent_asin
        ]
        
        if not child_asins:
            child_asins = [body.parent_asin] # Fallback
            
        # Update all children
        update_payload = {
            "reference_name": reference_name
        }
        if body.exclude_keywords is not None:
            update_payload["exclude_keywords"] = body.exclude_keywords.strip()
            
        resp = supabase.table("pb_client_listings").update(update_payload).in_("asin", child_asins).eq("client_id", body.client_id).execute()
        
        if not resp.data:
            product_by_asin = {p["asin"]: p for p in saddl_products}
            upsert_rows = []
            for asin in child_asins:
                product = product_by_asin.get(asin, {})
                mp_info = MARKETPLACE_MAP.get(product.get("marketplace_id"), {"name": "UAE"})
                row = {
                    "client_id": body.client_id,
                    "marketplace": mp_info["name"],
                    "asin": asin,
                    "sku_id": asin,
                    "reference_name": reference_name,
                }
                if body.exclude_keywords is not None:
                    row["exclude_keywords"] = body.exclude_keywords.strip()
                upsert_rows.append(row)
            resp = supabase.table("pb_client_listings").upsert(
                upsert_rows,
                on_conflict="client_id,asin,marketplace"
            ).execute()

        marketplaces = {
            MARKETPLACE_MAP.get(p.get("marketplace_id"), {"name": "UAE"})["name"]
            for p in saddl_products
            if p.get("asin") in child_asins or p.get("parent_asin") == body.parent_asin
        } or {"UAE"}
        for marketplace in marketplaces:
            _clear_parent_dashboard_rows(
                supabase,
                client_id=body.client_id,
                parent_asin=body.parent_asin,
                child_asins=child_asins,
                marketplace=marketplace,
            )

        # Recompare this parent immediately from its category_id pool(s), applying the saved keyword.
        analysis_result = recalculate_parent_from_categories(body.client_id, body.parent_asin)

        return {
            "status": "success",
            "message": f"Reference name updated for {len(child_asins)} variations. Re-analysis completed.",
            "updated_count": len(resp.data),
            "analysis": analysis_result,
        }
    except Exception as e:
        import traceback
        print(f"ERROR in update_reference_name: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
