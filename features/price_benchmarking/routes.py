"""
FastAPI routes for the price benchmarking module.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_client_id
from db import get_supabase_client

from .snapshot_service import calculate_transient_upload_analysis, _resolve_majority_categories
from .saddl_db import fetch_saddl_accounts, fetch_saddl_categories
from .discovery_service import run_competitor_analysis_workflow


def _load_account_parent_map(client_id: str) -> tuple[Dict[str, str], set[str]]:
    """Return child ASIN -> parent ASIN mapping and the allowed parent ASIN set for an account."""
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

    from .saddl_db import fetch_account_products_with_categories
    from .discovery_service import MARKETPLACE_MAP

    marketplace = "UAE"
    products = fetch_account_products_with_categories(client_id)
    if products:
        m_id = products[0].get("marketplace_id")
        marketplace = MARKETPLACE_MAP.get(m_id, {"name": "UAE"})["name"]

    org_id = f"{client_id}_org"
    supabase.table("pb_organizations").upsert({
        "org_id": org_id,
        "name": f"{client_id.replace('_', ' ').title()} Org",
        "type": "seller",
    }).execute()
    supabase.table("pb_clients").upsert({
        "client_id": client_id,
        "name": name or client_id.replace("_", " ").title(),
        "marketplace": marketplace,
        "org_id": org_id,
        "is_active": True,
    }).execute()
    return marketplace


def is_automation_enabled(supabase) -> bool:
    """Check if automation is globally enabled."""
    try:
        resp = supabase.table("pb_settings").select("value").eq("key", "automation_enabled").execute()
        if resp.data:
            return resp.data[0]["value"] is True
    except Exception as e:
        print(f"WARNING: Settings table not found: {e}")
    return True


router = APIRouter()


async def verify_client_access(
    client_id: str | None = Query(None),
    current_client_id: str = Depends(get_current_client_id),
):
    if client_id is None:
        return None
    if current_client_id != client_id and current_client_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this client's data")
    return client_id


async def require_internal_token(x_internal_token: str | None = Header(None, alias="X-Internal-Token")):
    expected = os.getenv("INTERNAL_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="Internal token not configured")
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token")


class CreateClientRequest(BaseModel):
    client_id: str
    name: str
    marketplace: str
    org_id: str
    sp_api_profile_id: str | None = None


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
    products: list[dict]


class UpdateReferenceNameRequest(BaseModel):
    client_id: str
    parent_asin: str
    reference_name: str
    exclude_keywords: str | None = None


class UpdateTierRequest(BaseModel):
    client_id: str
    asin: str
    competitive_tier: str | None = None


class UploadPriceRecord(BaseModel):
    asin: str
    marketplace: str
    floor_price: float | None = None
    buy_box_price: float | None = None
    category_name: str | None = "Uploaded"
    category_id: str | None = None
    title: str | None = None
    sales_rank: float | None = None
    bsr_rank: float | None = None
    rank: float | None = None
    brand: str | None = None
    rating: float | None = None
    reviews: int | None = None


class UploadDataRequest(BaseModel):
    records: list[UploadPriceRecord]
    persist: bool = True
    client_id: str | None = None
    products: list[dict[str, Any]] | None = None


@router.get("/accounts")
async def list_accounts():
    """List all Amazon accounts available for benchmarking from the SADDL DB."""
    accounts = fetch_saddl_accounts()
    return {"accounts": accounts}


@router.get("/account-bsr-categories")
async def get_account_bsr_categories(
    account_id: str = Query(...),
    supabase=Depends(get_supabase_client),
):
    """Fetch unique BSR categories for the selected account from the SADDL DB."""
    ensure_client_exists(supabase, account_id)
    categories = fetch_saddl_categories(account_id)

    resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords, competitive_tier").eq("client_id", account_id).execute()
    listings = resp.data or []

    from .saddl_db import fetch_account_products_with_categories
    saddl_products = fetch_account_products_with_categories(account_id)
    saddl_products = _resolve_majority_categories(saddl_products)

    child_to_parent = {p["asin"]: p["parent_asin"] for p in saddl_products}
    parent_to_resolved_category = {}
    parent_to_children: Dict[str, list] = {}
    for p in saddl_products:
        parent = p.get("parent_asin")
        cat_name = p.get("category_name")
        if parent and cat_name:
            parent_to_resolved_category[parent.strip()] = cat_name.strip()
        if parent:
            parent_to_children.setdefault(parent, [])
            if not any(c["asin"] == p["asin"] for c in parent_to_children[parent]):
                parent_to_children[parent].append({"asin": p["asin"], "title": p.get("title", p["asin"])})

    # Build per-child tier map from pb_client_listings
    child_tier_map: Dict[str, str | None] = {l["asin"]: l.get("competitive_tier") for l in listings}

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
            ranks = [prod["rank"] for prod in filtered_products if prod.get("rank") is not None]
            c["avg_rank"] = sum(ranks) / len(ranks) if ranks else 0.0
            filtered_categories.append(c)

    categories = filtered_categories

    parent_ref_map: Dict[str, str] = {}
    parent_exclude_map: Dict[str, str] = {}
    for l in listings:
        p_asin = child_to_parent.get(l["asin"], l["asin"])
        if l.get("reference_name"):
            parent_ref_map[p_asin] = l["reference_name"]
            parent_ref_map[l["asin"]] = l["reference_name"]
        if l.get("exclude_keywords"):
            parent_exclude_map[p_asin] = l["exclude_keywords"]
            parent_exclude_map[l["asin"]] = l["exclude_keywords"]

    asin_categories: Dict[str, set] = {}
    for p in saddl_products:
        cat = p.get("category_name")
        if cat:
            asin_categories.setdefault(p["asin"], set()).add(cat)
            asin_categories.setdefault(p["parent_asin"], set()).add(cat)

    for c in categories:
        for p in c.get("products", []):
            product_cats = asin_categories.get(p["asin"]) or set()
            p["category_name"] = ", ".join(sorted(product_cats))
            p["reference_name"] = parent_ref_map.get(p["asin"], "")
            p["exclude_keywords"] = parent_exclude_map.get(p["asin"], "")
            children = parent_to_children.get(p["asin"], [{"asin": p["asin"], "title": p.get("title", p["asin"])}])
            p["child_variants"] = [
                {**child, "competitive_tier": child_tier_map.get(child["asin"])}
                for child in children
            ]

    return {"categories": categories}


@router.post("/trigger-competitor-analysis")
async def trigger_competitor_analysis_route(
    account_id: str = Query(...),
    _token: None = Depends(require_internal_token),
):
    """
    Triggers the full competitor pricing analysis workflow for an account.
    Returns cached results if fresh, otherwise runs analysis immediately.
    """
    try:
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
    if current_client_id != body.client_id and current_client_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    resp = supabase.table("pb_client_listings").upsert(body.model_dump()).execute()
    return {"listing": (resp.data or [None])[0]}


@router.get("/overview")
async def get_overview(
    client_id: str = Query(...),
    tier: str = Query("All"),
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
    parent_titles_map: Dict[str, str] = {}
    parent_ref_map: Dict[str, str] = {}
    parent_asin_count = 0
    parent_children_map: Dict[str, list] = {}
    try:
        from .saddl_db import fetch_account_products_with_categories, fetch_saddl_categories
        saddl_products, categories = await asyncio.gather(
            asyncio.to_thread(fetch_account_products_with_categories, client_id),
            asyncio.to_thread(fetch_saddl_categories, client_id),
        )
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
            filtered_products = [
                p for p in c.get("products", [])
                if not p.get("asin") or (
                    parent_to_resolved_category.get(p["asin"].strip(), "").strip().lower() == c_name_norm
                    or not parent_to_resolved_category.get(p["asin"].strip())
                )
            ]
            if filtered_products:
                c["products"] = filtered_products
                c["asin_count"] = len(filtered_products)
                filtered_categories.append(c)

        parent_asin_count = sum(c["asin_count"] for c in filtered_categories)

        listings_resp = supabase.table("pb_client_listings").select("asin, sku_id, reference_name, exclude_keywords").eq("client_id", client_id).execute()
        listings = listings_resp.data or []
        sku_map = {l["asin"]: l.get("sku_id") for l in listings}
        seen_ch: set = set()
        for p in saddl_products:
            par = p.get("parent_asin") or p.get("asin")
            ch = p.get("asin")
            if par and ch and ch not in seen_ch:
                seen_ch.add(ch)
                parent_children_map.setdefault(par, []).append({
                    "asin": ch,
                    "sku": sku_map.get(ch) or ch,
                    "title": p.get("title") or ch,
                })
        parent_exclude_map: Dict[str, str] = {}
        for l in listings:
            asin = l.get("asin")
            p_asin = child_to_parent.get(asin, asin)
            if asin and l.get("reference_name"):
                parent_ref_map[p_asin] = l["reference_name"]
            if asin and l.get("exclude_keywords"):
                parent_exclude_map[p_asin] = l["exclude_keywords"]
    except Exception as e:
        print(f"Warning: Failed to fetch parent ASIN mapping for overview: {e}")

    snapshot_rows = _latest_snapshots_by_parent(rows, child_to_parent)

    asin_list = [r["asin"] for r in snapshot_rows if r.get("asin")]
    rating_map: Dict[str, float] = {}
    reviews_map: Dict[str, int] = {}
    if asin_list:
        try:
            from .sc_raw_client import get_latest_competitor_prices
            marketplace_id = "A2VIGQ35RCS4UG"  # Default UAE
            latest_prices = get_latest_competitor_prices(marketplace_id, days_back=7)
            for asin in asin_list:
                if asin in latest_prices:
                    data = latest_prices[asin]
                    if data.get("rating") is not None:
                        rating_map[asin] = data["rating"]
                    if data.get("reviews") is not None:
                        reviews_map[asin] = data["reviews"]
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
        "child_products": parent_children_map,
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
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }
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


@router.get("/recommendations")
async def get_recommendations(
    client_id: str = Query(...),
    tier: str = Query("All"),
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

    from .saddl_db import fetch_account_prices, fetch_account_products_with_categories

    saddl_products: List[Dict] = []
    live_prices: Dict[str, float] = {}
    child_to_parent: Dict[str, str] = {}
    parent_asins: set[str] = set()
    try:
        saddl_products, live_prices = await asyncio.gather(
            asyncio.to_thread(fetch_account_products_with_categories, client_id),
            asyncio.to_thread(fetch_account_prices, client_id),
        )
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }
        parent_asins = {p for p in child_to_parent.values() if p}
    except Exception as e:
        print(f"Warning: Failed to fetch SADDL data for recommendations: {e}")

    recs = _latest_recommendations_by_parent(resp.data or [], child_to_parent, parent_asins)

    parent_titles_map: Dict[str, str] = {}
    parent_ref_map: Dict[str, str] = {}
    try:
        for p in saddl_products:
            p_asin = p.get("parent_asin") or p.get("asin")
            title = p.get("title")
            if p_asin and title and title != p_asin:
                if p_asin not in parent_titles_map or len(title) > len(parent_titles_map[p_asin]):
                    parent_titles_map[p_asin] = title

        listings_resp = supabase.table("pb_client_listings").select("asin, reference_name, exclude_keywords").eq("client_id", client_id).execute()
        parent_exclude_map: Dict[str, str] = {}
        for l in listings_resp.data or []:
            asin = l.get("asin")
            p_asin = child_to_parent.get(asin, asin)
            if asin and l.get("reference_name"):
                parent_ref_map[p_asin] = l["reference_name"]
            if asin and l.get("exclude_keywords"):
                parent_exclude_map[p_asin] = l["exclude_keywords"]

        parent_prices_map: Dict[str, list] = {}
        for child_asin, price in live_prices.items():
            if price is not None and price > 0:
                p_asin = child_to_parent.get(child_asin, child_asin)
                parent_prices_map.setdefault(p_asin, []).append(float(price))

        for r in recs:
            parent_asin = r.get("parent_asin") or r.get("asin")
            variation_prices = parent_prices_map.get(parent_asin)
            if variation_prices:
                r["current_price"] = round(sum(variation_prices) / len(variation_prices), 2)
            else:
                metadata = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
                for asin_key in [r.get("asin"), r.get("parent_asin"), metadata.get("representative_child_asin")]:
                    if asin_key in live_prices:
                        r["current_price"] = live_prices[asin_key]
                        break
    except Exception as e:
        print(f"Warning: Failed to fetch live prices/titles for recommendations: {e}")

    for r in recs:
        parent_asin = r.get("parent_asin") or r.get("asin")
        r["title"] = parent_titles_map.get(parent_asin) or ""
        r["reference_name"] = parent_ref_map.get(parent_asin) or ""
        r["exclude_keywords"] = parent_exclude_map.get(parent_asin) or ""

    try:
        comp_asins: set[str] = set()
        for r in recs:
            meta = r.get("metadata")
            if isinstance(meta, dict):
                for c in meta.get("competitors", []):
                    if isinstance(c, dict) and c.get("asin"):
                        comp_asins.add(c["asin"])

        if comp_asins:
            comp_data_resp = (
                supabase.table("competitor_products")
                .select("competitor_asin, rating, reviews, brand")
                .in_("competitor_asin", list(comp_asins))
                .execute()
            )
            comp_map: Dict[str, dict] = {}
            for row in comp_data_resp.data or []:
                casin = row["competitor_asin"]
                if casin not in comp_map:
                    comp_map[casin] = row

            for r in recs:
                meta = r.get("metadata")
                if isinstance(meta, dict):
                    for c in meta.get("competitors", []):
                        if isinstance(c, dict) and c.get("asin"):
                            info = comp_map.get(c["asin"])
                            if info:
                                if info.get("rating") is not None:
                                    c["rating"] = float(info["rating"])
                                if info.get("reviews") is not None:
                                    c["reviews"] = int(info["reviews"])
                                if info.get("brand") is not None:
                                    c["brand"] = info["brand"]
    except Exception as enrich_err:
        print(f"Warning: Failed to enrich competitor metadata: {enrich_err}")

    return {"recommendations": recs}


@router.post("/upload-data")
async def upload_data(
    body: UploadDataRequest,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client),
):
    """
    Upload competitor data for simulation analysis.
    When persist=False, runs transient analysis and returns results immediately.
    When persist=True, saves records to sc_raw.competitor_pricing via direct SQL.
    """
    if not body.records:
        return {"status": "success", "processed": 0}

    if not body.persist:
        if not body.client_id:
            raise HTTPException(status_code=400, detail="client_id is required for transient analysis")
        if body.products is None:
            raise HTTPException(
                status_code=400,
                detail="Simulation mode requires uploaded product details.",
            )
        results = calculate_transient_upload_analysis(
            client_id=body.client_id,
            products=body.products,
            competitor_records=[rec.model_dump() for rec in body.records],
        )
        return {"status": "success", "mode": "simulation", "source": "uploaded_files_only", "results": results}

    from datetime import datetime, date, timezone
    import psycopg2
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")
    if not SADDL_DATABASE_URL:
        raise HTTPException(status_code=500, detail="SADDL_DATABASE_URL not configured")
    
    now_iso = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()
    
    conn = psycopg2.connect(SADDL_DATABASE_URL)
    cur = conn.cursor()
    try:
        inserted = 0
        for rec in body.records:
            row = rec.model_dump()
            price = row.get("floor_price") or row.get("buy_box_price")
            if price is None:
                continue
            cur.execute("""
                INSERT INTO sc_raw.competitor_pricing 
                (report_date, marketplace_id, category_id, rank, asin, title, price, price_numeric, currency, 
                 rating, reviews_count, product_url, image_url, pulled_at, account_id, category_name, brand)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                today,  # report_date
                "A2VIGQ35RCS4UG",  # marketplace_id (UAE default)
                row.get("category_id") or "0",  # category_id
                row.get("sales_rank") or row.get("bsr_rank") or row.get("rank") or 0,  # rank
                row["asin"],  # asin
                row.get("title") or row["asin"],  # title
                str(price),  # price (text)
                float(price),  # price_numeric
                "AED",  # currency
                row.get("rating"),  # rating
                row.get("reviews"),  # reviews_count
                None,  # product_url
                None,  # image_url
                now_iso,  # pulled_at
                "manual_upload",  # account_id
                row.get("category_name") or "Uploaded",  # category_name
                row.get("brand"),  # brand
            ))
            inserted += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert competitor pricing: {e}")
    finally:
        cur.close()
        conn.close()

    return {"status": "success", "processed": inserted}


@router.post("/onboard-products")
async def onboard_products(
    body: OnboardProductsRequest,
    supabase=Depends(get_supabase_client),
):
    """Onboard the client's own product list into pb_benchmarking_skus and pb_client_listings."""
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
            "is_active": True,
        })
        listing_rows.append({
            "client_id": body.client_id,
            "marketplace": body.marketplace,
            "asin": asin,
            "sku_id": sku,
            "listing_price": price,
            "currency": curr,
        })
    if sku_rows:
        supabase.table("pb_benchmarking_skus").upsert(sku_rows, on_conflict="client_id,sku_id,marketplace").execute()
    if listing_rows:
        supabase.table("pb_client_listings").upsert(listing_rows, on_conflict="client_id,asin,marketplace").execute()
    return {"status": "success", "registered": len(sku_rows)}


@router.get("/client-listings")
async def get_client_listings(
    client_id: str = Query(...),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    """Fetch all product listings for a client, grouped by parent ASIN."""
    from .saddl_db import fetch_account_products_with_categories
    saddl_products = fetch_account_products_with_categories(client_id)
    parent_map = {
        p["asin"]: p["parent_asin"]
        for p in saddl_products
        if p.get("asin") and p.get("parent_asin")
    }
    resp = supabase.table("pb_client_listings").select("*").eq("client_id", client_id).execute()
    listings = resp.data or []

    grouped: Dict[str, dict] = {}
    for l in listings:
        parent = parent_map.get(l["asin"], l["asin"])
        if parent not in grouped:
            grouped[parent] = {
                "parent_asin": parent,
                "reference_name": l.get("reference_name") or "",
                "exclude_keywords": l.get("exclude_keywords") or "",
                "children": [],
            }
        grouped[parent]["children"].append(l)
        if l.get("reference_name"):
            grouped[parent]["reference_name"] = l["reference_name"]
        if l.get("exclude_keywords"):
            grouped[parent]["exclude_keywords"] = l["exclude_keywords"]

    return {"grouped_listings": list(grouped.values())}


@router.post("/update-reference-name")
async def update_reference_name(
    body: UpdateReferenceNameRequest,
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

        child_asins = [
            p["asin"] for p in saddl_products
            if p["parent_asin"] == body.parent_asin or p["asin"] == body.parent_asin
        ] or [body.parent_asin]

        update_payload: dict = {"reference_name": reference_name}
        if body.exclude_keywords is not None:
            update_payload["exclude_keywords"] = body.exclude_keywords.strip()

        resp = (
            supabase.table("pb_client_listings")
            .update(update_payload)
            .in_("asin", child_asins)
            .eq("client_id", body.client_id)
            .execute()
        )

        if not resp.data:
            product_by_asin = {p["asin"]: p for p in saddl_products}
            upsert_rows = []
            for asin in child_asins:
                product = product_by_asin.get(asin, {})
                mp_info = MARKETPLACE_MAP.get(product.get("marketplace_id"), {"name": "UAE"})
                row: dict = {
                    "client_id": body.client_id,
                    "marketplace": mp_info["name"],
                    "asin": asin,
                    "sku_id": asin,
                    "reference_name": reference_name,
                }
                if body.exclude_keywords is not None:
                    row["exclude_keywords"] = body.exclude_keywords.strip()
                upsert_rows.append(row)
            supabase.table("pb_client_listings").upsert(
                upsert_rows, on_conflict="client_id,asin,marketplace"
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


@router.post("/recalculate-dashboard")
async def recalculate_dashboard(
    client_id: str = Query(...),
    tier: str = Query("All"),
    _: str = Depends(verify_client_access),
    supabase=Depends(get_supabase_client),
):
    """
    Recalculates the dashboard overview and recommendations using only competitors
    from the selected tier. Does NOT persist to the database.
    """
    try:
        from .tier_service import filter_competitors_by_tier
        from .benchmarking import compute_benchmark, CompetitorPrice
        from .recommendations import recommend, RepricingStrategy

        # 1. Fetch current recommendations to get the full raw competitor lists
        recs_resp = supabase.table("pb_recommendations").select("*").eq("client_id", client_id).execute()
        recs = recs_resp.data or []

        # 2. Recompute for each row
        recalculated_recs = []
        recalculated_snapshots = []
        
        for row in recs:
            meta = row.get("metadata") or {}
            raw_competitors = meta.get("competitors") or []
            
            # Apply universal tier filter using the reusable backend helper
            filtered_competitors = filter_competitors_by_tier(raw_competitors, tier)
            
            # Convert to CompetitorPrice objects
            comp_objs = [
                CompetitorPrice(
                    asin=c.get("asin"),
                    title=c.get("title"),
                    price=float(c.get("floor_price") or c.get("price") or 0),
                    is_fba=c.get("is_buy_box_winner", False),
                    brand=c.get("brand"),
                    rating=c.get("rating"),
                    reviews=c.get("reviews"),
                ) for c in filtered_competitors if float(c.get("floor_price") or c.get("price") or 0) > 0
            ]
            
            # Calculate new benchmark
            benchmark = compute_benchmark(
                sku_id=row["sku_id"],
                asin=row["asin"],
                your_price=float(row.get("current_price") or row.get("your_price") or 0),
                competitors=comp_objs,
                marketplace=row.get("marketplace") or "UAE",
            )
            
            if not benchmark:
                continue
                
            strategy_str = row.get("strategy")
            try:
                strategy = RepricingStrategy(strategy_str)
            except:
                strategy = RepricingStrategy.MID
                
            new_rec = recommend(
                result=benchmark,
                strategy=strategy,
                min_price=None,
                max_price=None,
            )
            
            # Build modified recommendation row
            mod_rec = dict(row)
            mod_rec["recommended_price"] = new_rec.recommended_price
            mod_rec["change_amount"] = new_rec.change_amount
            mod_rec["change_pct"] = new_rec.change_pct
            mod_rec["action"] = new_rec.action
            mod_rec["reasoning"] = new_rec.reasoning
            # Update metadata to include ONLY the filtered competitors so charts update
            new_meta = dict(new_rec.metadata)
            new_meta["competitors"] = filtered_competitors
            mod_rec["metadata"] = new_meta
            recalculated_recs.append(mod_rec)
            
            # Build modified snapshot row
            mod_snap = {
                "client_id": client_id,
                "sku_id": row["sku_id"],
                "asin": row["asin"],
                "parent_asin": row.get("parent_asin"),
                "snapshot_date": row.get("snapshot_date"),
                "your_price": benchmark.your_price,
                "n_competitors": benchmark.n_competitors,
                "floor_price": benchmark.floor,
                "ceiling_price": benchmark.ceiling,
                "median_price": benchmark.median,
                "p25_price": benchmark.p25,
                "p75_price": benchmark.p75,
                "percentile_rank": benchmark.percentile_rank,
                "index_vs_median": benchmark.index_vs_median,
                "zone": benchmark.zone.value,
            }
            recalculated_snapshots.append(mod_snap)

        # Collect unique parent ASINs from the full unfiltered recs list so the
        # frontend can verify the universe count hasn't changed between tier switches.
        all_parent_asins = set()
        for row in recs:
            pa = row.get("parent_asin") or row.get("asin")
            if pa:
                all_parent_asins.add(pa)
        total_parent_asin_count = len(all_parent_asins)

        tier_parent_asins = set()
        for snap in recalculated_snapshots:
            pa = snap.get("parent_asin") or snap.get("asin")
            if pa:
                tier_parent_asins.add(pa)

        print(f"[VALIDATION] recalculate-dashboard tier='{tier}': "
              f"total_universe={total_parent_asin_count} parent ASINs | "
              f"tier_filtered={len(tier_parent_asins)} parent ASINs with valid competitor data")

        return {
            "status": "success",
            "snapshots": recalculated_snapshots,
            "recommendations": recalculated_recs,
            "tier": tier,
            # IMPORTANT: The parent_asin_count always reflects the TOTAL tracked universe,
            # NOT the count of ASINs in the selected tier. This ensures the frontend
            # KPI "Tracked Parent ASINs" stays consistent across all tier selections.
            "parent_asin_count": total_parent_asin_count,
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=error_details)


@router.get("/competitor-tiers")
async def get_competitor_tiers(
    account_id: str = Query(...),
    asin: str = Query(...),
    supabase=Depends(get_supabase_client),
):
    """Return auto-detected price tiers for a child ASIN's filtered competitor pool."""
    from .saddl_db import fetch_account_products_with_categories, fetch_parent_asin_categories, fetch_competitor_pricing_by_category
    from .benchmarking import detect_price_tiers
    from .relevance_filter import filter_related_products

    products_data = await asyncio.to_thread(fetch_account_products_with_categories, account_id)
    product = next((p for p in products_data if p["asin"] == asin), None)
    if not product:
        raise HTTPException(status_code=404, detail=f"ASIN {asin} not found for account {account_id}")

    parent_asin = product["parent_asin"]
    cats = await asyncio.to_thread(fetch_parent_asin_categories, account_id, parent_asin)
    own_asins = {p["asin"] for p in products_data}

    merged: list[dict] = []
    seen: set[str] = set()
    for cat in cats:
        cat_id, mp_id = cat.get("category_id"), cat.get("marketplace_id")
        if not cat_id or not mp_id:
            continue
        for comp in fetch_competitor_pricing_by_category(cat_id, mp_id):
            if comp["asin"] not in seen:
                seen.add(comp["asin"])
                merged.append(comp)

    listing_resp = supabase.table("pb_client_listings").select("reference_name,exclude_keywords,competitive_tier").eq("client_id", account_id).eq("asin", asin).execute()
    listing = listing_resp.data[0] if listing_resp.data else {}
    filtered = filter_related_products({**product, **listing}, merged, exclude_asins=own_asins)

    prices = [float(c["price"]) for c in filtered if c.get("price") and float(c["price"]) > 0]
    tiers = detect_price_tiers(prices)
    return {
        "asin": asin,
        "parent_asin": parent_asin,
        "current_tier": listing.get("competitive_tier"),
        "total_competitors": len(filtered),
        "tiers": [{"label": t.label, "min_price": round(t.min_price, 2), "max_price": round(t.max_price, 2), "count": t.count, "median": round(t.median, 2)} for t in tiers],
    }


@router.post("/update-tier")
async def update_competitive_tier(
    body: UpdateTierRequest,
    current_client_id: str = Depends(get_current_client_id),
    supabase=Depends(get_supabase_client),
):
    """Persist competitive tier for a child ASIN then trigger recalculation."""
    if current_client_id != body.client_id and current_client_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    result = supabase.table("pb_client_listings").update({"competitive_tier": body.competitive_tier}).eq("client_id", body.client_id).eq("asin", body.asin).execute()
    if not result.data:
        supabase.table("pb_client_listings").insert({"client_id": body.client_id, "asin": body.asin, "sku_id": body.asin, "marketplace": "UAE", "competitive_tier": body.competitive_tier}).execute()

    from .discovery_service import recalculate_parent_from_categories
    from .saddl_db import fetch_account_products_with_categories
    products = await asyncio.to_thread(fetch_account_products_with_categories, body.client_id)
    product = next((p for p in products if p["asin"] == body.asin), None)
    analysis = (
        await asyncio.to_thread(recalculate_parent_from_categories, body.client_id, product["parent_asin"])
        if product else {"status": "skipped"}
    )
    return {"status": "ok", "asin": body.asin, "competitive_tier": body.competitive_tier, "analysis": analysis}


@router.get("/automation-status")
async def get_automation_status(supabase=Depends(get_supabase_client)):
    return {"enabled": is_automation_enabled(supabase)}


@router.post("/toggle-automation")
async def toggle_automation(
    enabled: bool,
    _token: None = Depends(require_internal_token),
    supabase=Depends(get_supabase_client),
):
    supabase.table("pb_settings").upsert({"key": "automation_enabled", "value": enabled}).execute()
    return {"status": "ok", "enabled": enabled}


def _latest_recommendations_by_parent(
    recommendations: List[Dict[str, Any]],
    child_to_parent: Dict[str, str] | None = None,
    allowed_parent_asins: set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Keep the newest pending recommendation for each parent group."""
    child_to_parent = child_to_parent or {}
    allowed_parent_asins = allowed_parent_asins or set()

    def sort_key(row: Dict[str, Any]) -> tuple:
        is_parent_row = int(bool(row.get("parent_asin")) and row.get("asin") == row.get("parent_asin"))
        return (str(row.get("created_at") or ""), str(row.get("snapshot_date") or ""), is_parent_row)

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
    """Keep the newest snapshot for each parent group."""
    child_to_parent = child_to_parent or {}

    def sort_key(row: Dict[str, Any]) -> tuple:
        is_parent_row = int(bool(row.get("parent_asin")) and row.get("asin") == row.get("parent_asin"))
        return (str(row.get("snapshot_date") or ""), str(row.get("created_at") or ""), is_parent_row)

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
