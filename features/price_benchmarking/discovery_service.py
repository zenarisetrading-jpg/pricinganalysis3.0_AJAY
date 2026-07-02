"""
Competitor analysis orchestration.
Reads competitor pricing data directly from sc_raw.competitor_pricing via the SADDL DB.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from db import get_supabase_client
from .saddl_db import (
    fetch_account_products_with_categories,
    fetch_all_parent_categories,
    fetch_parent_asin_categories,
    fetch_account_prices,
    fetch_account_performance,
    fetch_competitor_pricing_by_category,
)
from .snapshot_service import calculate_transient_upload_analysis
from .relevance_filter import filter_related_products

MARKETPLACE_MAP = {
    "A2VIGQ35RCS4UG": {"domain": "amazon.ae", "name": "UAE"},
    "A17E79C6D8DWNP": {"domain": "amazon.sa", "name": "KSA"},
}


def get_cached_analysis(asin: str, marketplace: str):
    """Fetch recent analysis from the database (fresh within 24 hours)."""
    sb = get_supabase_client()
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    resp = (
        sb.table("pricing_analysis")
        .select("*")
        .eq("asin", asin)
        .eq("marketplace", marketplace)
        .gt("updated_at", yesterday)
        .execute()
    )
    return resp.data[0] if resp.data else None


def save_competitor_data(
    parent_asin: str,
    marketplace: str,
    competitors: List[Dict],
    product_asins: List[str] | None = None,
) -> None:
    """Persist filtered competitor details for a parent ASIN group."""
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
            "relevance_score": c.get("relevance_score", 1.0),
        })
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


def save_pricing_analysis(
    asin: str,
    marketplace: str,
    results: Dict,
    *,
    parent_asin: str | None = None,
    skip_clear: bool = False,
) -> None:
    """Persist pricing analysis summary and populate all dashboard tables."""
    actual_parent = parent_asin or asin
    sb = get_supabase_client()

    snap = next((s for s in results.get("snapshots", []) if s["asin"] == asin), None)
    if not snap and results.get("snapshots"):
        snap = results["snapshots"][0]
    if not snap:
        print(f"WARNING: No snapshot found for ASIN {asin}. Proceeding with defaults.")
        snap = {}

    rec = next((r for r in results.get("recommendations", []) if r["asin"] == asin), None)
    if not rec and results.get("recommendations"):
        rec = results["recommendations"][0]

    sb.table("pricing_analysis").upsert({
        "asin": asin,
        "marketplace": marketplace,
        "lowest_price": snap.get("floor_price"),
        "highest_price": snap.get("ceiling_price"),
        "average_price": snap.get("average_price"),
        "median_price": snap.get("median_price"),
        "recommended_price": rec.get("recommended_price") if rec else None,
        "premium_price": snap.get("p75_price"),
        "value_price": snap.get("p25_price"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="asin,marketplace").execute()

    account_id = results.get("client_id") or "unknown"
    child_asins = [
        row.get("asin")
        for row in [*results.get("snapshots", []), *results.get("recommendations", [])]
        if row.get("asin")
    ]

    sb.table("pb_client_snapshots_daily").upsert({
        "client_id": account_id,
        "asin": asin,
        "sku_id": snap.get("sku_id") or asin,
        "parent_asin": actual_parent,
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
        "strategy": snap.get("strategy"),
    }, on_conflict="client_id,asin,snapshot_date").execute()

    if not skip_clear:
        _clear_parent_dashboard_rows(
            sb,
            client_id=account_id,
            parent_asin=actual_parent,
            child_asins=child_asins,
            marketplace=marketplace,
        )

    all_recs = results.get("recommendations", [])
    if all_recs:
        representative_rec = next((r for r in all_recs if r.get("asin") == asin), all_recs[0])
        representative_snap = next(
            (s for s in results.get("snapshots", []) if s.get("asin") == representative_rec.get("asin")),
            snap,
        ) or {}
        category_ids = sorted({
            str(cat_id)
            for product in results.get("products", [])
            for cat_id in (product.get("category_ids") or [product.get("category_id")])
            if cat_id
        })
        metadata = dict(representative_rec.get("metadata") or representative_snap.get("metadata") or {})
        metadata.setdefault("n_competitors", representative_snap.get("n_competitors"))
        if category_ids:
            metadata["category_ids"] = category_ids
        if representative_rec.get("asin") and representative_rec.get("asin") != asin:
            metadata["representative_child_asin"] = representative_rec["asin"]

        try:
            sb.table("pb_recommendations").insert({
                "client_id": account_id,
                "sku_id": representative_rec.get("sku_id") or representative_snap.get("sku_id") or asin,
                "asin": asin,
                "parent_asin": actual_parent,
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
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            print(f"Saved parent recommendation for {asin}")
        except Exception as e:
            print(f"FAILED to save recommendation for {asin}: {e}")

    alert_rows = []
    for a in results.get("alerts", []):
        a_asin = a.get("asin") if isinstance(a, dict) else getattr(a, "asin", None)
        if a_asin == asin or a_asin is None:
            is_obj = hasattr(a, "alert_type")
            alert_rows.append({
                "client_id": account_id,
                "asin": asin,
                "parent_asin": actual_parent,
                "sku_id": snap.get("sku_id") or asin,
                "marketplace": marketplace,
                "alert_type": a.alert_type.value if is_obj else (a.get("type") or "price_alert"),
                "severity": a.severity.value if is_obj else (a.get("severity") or "medium"),
                "title": a.title if is_obj else (a.get("title") or "Price Alert"),
                "message": a.message if is_obj else (a.get("message") or "Check product pricing vs competitors."),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    if alert_rows:
        sb.table("pb_alerts").insert(alert_rows).execute()



def save_pricing_analysis_batch(
    analyses: List[Dict[str, Any]],
    marketplace: str,
    parent_asin: str | None = None,
    skip_clear: bool = False,
) -> None:
    """Batch persist pricing analysis summary and populate all dashboard tables."""
    if not analyses:
        return
        
    sb = get_supabase_client()
    actual_parent = parent_asin
    account_id = "unknown"
    child_asins = []
    
    pricing_analysis_rows = []
    snapshot_rows = []
    recommendation_rows = []
    alert_rows = []
    
    for entry in analyses:
        asin = entry.get("asin")
        if not asin:
            continue
        results = entry.get("results", {})
        account_id = results.get("client_id") or account_id
        
        snap = next((s for s in results.get("snapshots", []) if s.get("asin") == asin), None)
        if not snap and results.get("snapshots"):
            snap = results["snapshots"][0]
        if not snap:
            print(f"WARNING: No snapshot found for ASIN {asin}. Proceeding with defaults.")
            snap = {}

        rec = next((r for r in results.get("recommendations", []) if r.get("asin") == asin), None)
        if not rec and results.get("recommendations"):
            rec = results["recommendations"][0]
        if not rec:
            rec = {}

        child_asins.extend([
            row.get("asin")
            for row in [*results.get("snapshots", []), *results.get("recommendations", [])]
            if row.get("asin")
        ])
        
        pricing_analysis_rows.append({
            "asin": asin,
            "marketplace": marketplace,
            "lowest_price": snap.get("floor_price"),
            "highest_price": snap.get("ceiling_price"),
            "average_price": snap.get("average_price"),
            "median_price": snap.get("median_price"),
            "recommended_price": rec.get("recommended_price"),
            "premium_price": snap.get("p75_price"),
            "value_price": snap.get("p25_price"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        
        snapshot_rows.append({
            "client_id": account_id,
            "asin": asin,
            "sku_id": snap.get("sku_id") or asin,
            "parent_asin": actual_parent or asin,
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
            "strategy": snap.get("strategy"),
        })
        
        all_recs = results.get("recommendations", [])
        if all_recs:
            representative_rec = next((r for r in all_recs if r.get("asin") == asin), all_recs[0])
            representative_snap = next(
                (s for s in results.get("snapshots", []) if s.get("asin") == representative_rec.get("asin")),
                snap,
            ) or {}
            category_ids = sorted({
                str(cat_id)
                for product in results.get("products", [])
                for cat_id in (product.get("category_ids") or [product.get("category_id")])
                if cat_id
            })
            metadata = dict(representative_rec.get("metadata") or representative_snap.get("metadata") or {})
            metadata.setdefault("n_competitors", representative_snap.get("n_competitors"))
            if category_ids:
                metadata["category_ids"] = category_ids
            if representative_rec.get("asin") and representative_rec.get("asin") != asin:
                metadata["representative_child_asin"] = representative_rec["asin"]

            recommendation_rows.append({
                "client_id": account_id,
                "sku_id": representative_rec.get("sku_id") or representative_snap.get("sku_id") or asin,
                "asin": asin,
                "parent_asin": actual_parent or asin,
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
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        for a in results.get("alerts", []):
            a_asin = a.get("asin") if isinstance(a, dict) else getattr(a, "asin", None)
            if a_asin == asin or a_asin is None:
                is_obj = hasattr(a, "alert_type")
                alert_rows.append({
                    "client_id": account_id,
                    "asin": asin,
                    "parent_asin": actual_parent or asin,
                    "sku_id": snap.get("sku_id") or asin,
                    "marketplace": marketplace,
                    "alert_type": a.alert_type.value if is_obj else (a.get("type") or "price_alert"),
                    "severity": a.severity.value if is_obj else (a.get("severity") or "medium"),
                    "title": a.title if is_obj else (a.get("title") or "Price Alert"),
                    "message": a.message if is_obj else (a.get("message") or "Check product pricing vs competitors."),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

    child_asins = list(set(child_asins))
    
    try:
        if pricing_analysis_rows:
            sb.table("pricing_analysis").upsert(pricing_analysis_rows, on_conflict="asin,marketplace").execute()
        if snapshot_rows:
            sb.table("pb_client_snapshots_daily").upsert(snapshot_rows, on_conflict="client_id,asin,snapshot_date").execute()
        
        if not skip_clear:
            _clear_parent_dashboard_rows(
                sb,
                client_id=account_id,
                parent_asin=actual_parent,
                child_asins=child_asins,
                marketplace=marketplace,
            )
            
        if recommendation_rows:
            sb.table("pb_recommendations").insert(recommendation_rows).execute()
            
        if alert_rows:
            sb.table("pb_alerts").insert(alert_rows).execute()
            
        print(f"Batch saved {len(analyses)} records for parent {actual_parent}")
    except Exception as e:
        print(f"FAILED batch save for parent {actual_parent}: {e}")


def _append_unique_category(categories: List[Dict[str, Any]], product: Dict[str, Any]) -> None:
    """Append a category from a product dict if not already present in the list."""
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


def _build_child_analysis_products(
    *,
    sb,
    account_id: str,
    parent_asin: str,
    parent_products: List[Dict[str, Any]],
    marketplace: str,
    category_ids: List[str],
    actual_prices: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Build one pricing analysis input per child ASIN, each with its own price and tier."""
    child_asins = [p["asin"] for p in parent_products if p.get("asin")]
    listing_rows: list[dict] = []
    try:
        resp = (
            sb.table("pb_client_listings")
            .select("*")
            .eq("client_id", account_id)
            .in_("asin", [*child_asins, parent_asin])
            .execute()
        )
        listing_rows = resp.data or []
    except Exception as e:
        print(f"Warning: Failed to fetch listings for parent {parent_asin}: {e}")

    listing_by_asin = {row["asin"]: row for row in listing_rows if row.get("asin")}
    parent_listing = listing_by_asin.get(parent_asin, {})

    products = []
    for p in parent_products:
        child_asin = p.get("asin")
        if not child_asin:
            continue
        listing = listing_by_asin.get(child_asin, {})
        price = float(
            listing.get("listing_price")
            or listing.get("price")
            or actual_prices.get(child_asin)
            or 0.0
        )
        if price <= 0:
            continue
        products.append({
            "asin": child_asin,
            "sku_id": listing.get("sku_id") or child_asin,
            "price": price,
            "marketplace": marketplace,
            "category_id": category_ids[0] if category_ids else p.get("category_id"),
            "category_ids": category_ids,
            "strategy": listing.get("strategy") or parent_listing.get("strategy") or "mid",
            "min_price": listing.get("min_price") or parent_listing.get("min_price"),
            "max_price": listing.get("max_price") or parent_listing.get("max_price"),
            "parent_asin": parent_asin,
            "reference_name": listing.get("reference_name") or parent_listing.get("reference_name"),
            "exclude_keywords": listing.get("exclude_keywords") or parent_listing.get("exclude_keywords"),
            "competitive_tier": listing.get("competitive_tier"),
            "title": p.get("title") or child_asin,
        })
    return products


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
            if (
                listing_by_asin.get(asin, {}).get("listing_price")
                or listing_by_asin.get(asin, {}).get("price")
                or actual_prices.get(asin)
            )
        ),
        parent_asin,
    )
    child_prices = []
    for p in parent_products:
        c_asin = p.get("asin")
        if not c_asin:
            continue
        c_listing = listing_by_asin.get(c_asin, {})
        c_price = c_listing.get("listing_price") or c_listing.get("price") or actual_prices.get(c_asin)
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
        reference_name = next(
            (row.get("reference_name") for row in listing_rows if row.get("reference_name")), None
        )
    exclude_keywords = next(
        (row.get("exclude_keywords") for row in listing_rows if row.get("exclude_keywords")), None
    )

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


def fetch_competitors_by_category(category_id: str, marketplace_id: str) -> List[Dict]:
    """
    Fetch the competitor pool for a category from sc_raw.competitor_pricing.
    Injects category_id into each row for downstream filtering and saving.
    """
    rows = fetch_competitor_pricing_by_category(category_id, marketplace_id)
    for r in rows:
        r["category_id"] = str(category_id)
    return rows


def _merge_competitor(merged_competitors: List[Dict], seen_asins: Dict[str, int], item: Dict) -> None:
    """Deduplicate by ASIN, preferring entries with usable prices."""
    asin = item.get("asin") or item.get("competitor_asin")
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
        for key in ("floor_price", "price", "competitor_price", "category_id", "title", "competitor_title", "brand", "parent_asin", "rating", "reviews"):
            if existing.get(key) in (None, "") and item.get(key) not in (None, ""):
                existing[key] = item[key]


def trigger_background_discovery(account_id: str) -> Dict[str, Any]:
    """
    Run pricing analysis for all parent ASINs in an account.
    Reads competitor data from sc_raw.competitor_pricing via the SADDL DB.
    """
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        return {"status": "error", "message": f"No products found for account {account_id}"}

    actual_prices = fetch_account_prices(account_id)
    live_performance = fetch_account_performance(account_id)

    sb = get_supabase_client()
    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace: {e}")

    mp_name = "KSA" if client_marketplace == "KSA" else "UAE"

    all_parent_categories = fetch_all_parent_categories(account_id)

    parent_asin_map: Dict[str, Dict[str, Any]] = {}
    for p in products_data:
        parent_asin = p["parent_asin"]
        if not parent_asin:
            continue
        if parent_asin not in parent_asin_map:
            categories = list(all_parent_categories.get(parent_asin, []))
            parent_asin_map[parent_asin] = {"products": [], "categories": categories}
        parent_asin_map[parent_asin]["products"].append(p)
        _append_unique_category(parent_asin_map[parent_asin]["categories"], p)

    if account_id == "nothing_silly":
        for data in parent_asin_map.values():
            _append_unique_category(data["categories"], {"category_id": "15160028031", "marketplace_id": "A2VIGQ35RCS4UG", "category_name": "Fallback UAE"})
            _append_unique_category(data["categories"], {"category_id": "12373520031", "marketplace_id": "A2VIGQ35RCS4UG", "category_name": "Fallback UAE 2"})

    print(f"Processing {len(parent_asin_map)} parent ASINs for account {account_id}...")

    own_asins = {p["asin"] for p in products_data if p.get("asin")}
    processed = 0
    errors: List[Dict] = []

    for parent_asin, data in parent_asin_map.items():
        merged_competitors: List[Dict] = []
        seen_asins: Dict[str, int] = {}

        for cat in data["categories"]:
            cat_id = cat.get("category_id")
            mp_id = cat.get("marketplace_id")
            if not cat_id or not mp_id:
                continue
            for item in fetch_competitors_by_category(cat_id, mp_id):
                _merge_competitor(merged_competitors, seen_asins, item)

        if not merged_competitors:
            print(f"No competitors in sc_raw.competitor_pricing for parent {parent_asin}")
            continue

        target_product = data["products"][0].copy()
        child_asins = [p["asin"] for p in data["products"]]
        listing_resp = (
            sb.table("pb_client_listings")
            .select("reference_name, exclude_keywords")
            .in_("asin", [*child_asins, parent_asin])
            .execute()
        )
        for row in listing_resp.data or []:
            if row.get("reference_name"):
                target_product["reference_name"] = row["reference_name"]
            if row.get("exclude_keywords"):
                target_product["exclude_keywords"] = row["exclude_keywords"]
            if row.get("reference_name") or row.get("exclude_keywords"):
                break

        filtered_competitors = filter_related_products(target_product, merged_competitors, exclude_asins=own_asins)
        print(f"Parent {parent_asin}: {len(merged_competitors)} raw -> {len(filtered_competitors)} filtered competitors")

        save_competitor_data(
            parent_asin=parent_asin,
            marketplace=mp_name,
            competitors=filtered_competitors,
            product_asins=child_asins,
        )

        cat_ids = [str(c["category_id"]) for c in data["categories"] if c.get("category_id")]
        analysis_products = _build_child_analysis_products(
            sb=sb,
            account_id=account_id,
            parent_asin=parent_asin,
            parent_products=data["products"],
            marketplace=mp_name,
            category_ids=cat_ids,
            actual_prices=actual_prices,
        )
        if not analysis_products:
            print(f"No priced child ASINs for parent {parent_asin}, skipping")
            continue

        _clear_parent_dashboard_rows(
            sb,
            client_id=account_id,
            parent_asin=parent_asin,
            child_asins=child_asins,
            marketplace=mp_name,
        )

        child_processed = 0
        batch_analyses = []
        for child_product in analysis_products:
            child_filtered = filter_related_products(
                child_product, merged_competitors, exclude_asins=own_asins
            )
            try:
                child_results = calculate_transient_upload_analysis(
                    client_id=account_id,
                    products=[child_product],
                    competitor_records=child_filtered,
                )
                child_results["client_id"] = account_id
                child_results["performance"] = [
                    p for p in live_performance if p["asin"] == child_product["asin"]
                ]
                batch_analyses.append({
                    "asin": child_product["asin"],
                    "results": child_results,
                })
                child_processed += 1
            except Exception as e:
                import traceback
                traceback.print_exc()
                errors.append({"parent_asin": parent_asin, "child_asin": child_product["asin"], "error": str(e)})
                
        if batch_analyses:
            save_pricing_analysis_batch(batch_analyses, mp_name, parent_asin=parent_asin, skip_clear=True)
            
        if child_processed > 0:
            processed += 1

    return {
        "status": "completed",
        "parent_asin_count": len(parent_asin_map),
        "processed": processed,
        "errors": errors,
    }


def recalculate_parent_from_categories(account_id: str, parent_asin: str) -> Dict[str, Any]:
    """Recalculate one parent ASIN using its linked category pools from sc_raw.competitor_pricing."""
    products_data = fetch_account_products_with_categories(account_id)
    parent_products = [
        p for p in products_data
        if p.get("parent_asin") == parent_asin or p.get("asin") == parent_asin
    ]
    if not parent_products:
        return {"status": "error", "message": f"No products found for parent_asin {parent_asin}"}

    sb = get_supabase_client()
    actual_prices = fetch_account_prices(account_id)

    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace: {e}")

    mp_name = "KSA" if client_marketplace == "KSA" else "UAE"

    cats = fetch_parent_asin_categories(account_id, parent_asin)
    for product in parent_products:
        _append_unique_category(cats, product)

    if account_id == "nothing_silly":
        _append_unique_category(cats, {"category_id": "15160028031", "marketplace_id": "A2VIGQ35RCS4UG", "category_name": "Fallback UAE"})
        _append_unique_category(cats, {"category_id": "12373520031", "marketplace_id": "A2VIGQ35RCS4UG", "category_name": "Fallback UAE 2"})

    merged_competitors: List[Dict] = []
    seen_asins: Dict[str, int] = {}
    for cat in cats:
        cat_id = cat.get("category_id")
        mp_id = cat.get("marketplace_id")
        if not cat_id or not mp_id:
            continue
        for item in fetch_competitors_by_category(cat_id, mp_id):
            _merge_competitor(merged_competitors, seen_asins, item)

    child_asins = [p["asin"] for p in parent_products]

    if not merged_competitors:
        _clear_parent_dashboard_rows(
            sb,
            client_id=account_id,
            parent_asin=parent_asin,
            child_asins=child_asins,
            marketplace=mp_name,
        )
        cat_ids = [str(c["category_id"]) for c in cats if c.get("category_id")]
        return {
            "status": "no_competitors",
            "parent_asin": parent_asin,
            "category_ids": cat_ids,
            "message": "No competitors found in sc_raw.competitor_pricing for linked categories",
        }

    target_product = parent_products[0].copy()
    listing_resp = (
        sb.table("pb_client_listings")
        .select("reference_name, exclude_keywords")
        .eq("client_id", account_id)
        .in_("asin", [*child_asins, parent_asin])
        .execute()
    )
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
        marketplace=mp_name,
        competitors=filtered_competitors,
        product_asins=child_asins,
    )

    cat_ids = [str(c["category_id"]) for c in cats if c.get("category_id")]
    analysis_products = _build_child_analysis_products(
        sb=sb,
        account_id=account_id,
        parent_asin=parent_asin,
        parent_products=parent_products,
        marketplace=mp_name,
        category_ids=cat_ids,
        actual_prices=actual_prices,
    )
    if not analysis_products:
        return {"status": "no_priced_children", "parent_asin": parent_asin, "message": "No child ASINs with a known price."}

    _clear_parent_dashboard_rows(sb, client_id=account_id, parent_asin=parent_asin, child_asins=child_asins, marketplace=mp_name)

    child_processed = 0
    batch_analyses = []
    for child_product in analysis_products:
        child_filtered = filter_related_products(child_product, merged_competitors, exclude_asins=own_asins)
        child_results = calculate_transient_upload_analysis(
            client_id=account_id, products=[child_product], competitor_records=child_filtered,
        )
        child_results["client_id"] = account_id
        batch_analyses.append({
            "asin": child_product["asin"],
            "results": child_results,
        })
        child_processed += 1
        
    save_pricing_analysis_batch(batch_analyses, mp_name, parent_asin=parent_asin, skip_clear=True)

    return {
        "status": "success",
        "parent_asin": parent_asin,
        "category_ids": cat_ids,
        "children_analyzed": child_processed,
        "category_competitors": len(merged_competitors),
        "filtered_competitors": len(filtered_competitors),
        "message": f"Recalculated {child_processed} child ASINs under {parent_asin} from {len(cat_ids)} category pool(s).",
    }


def run_competitor_analysis_workflow(account_id: str) -> Dict[str, Any]:
    """
    Unified entry point for the analysis workflow.
    Returns cached results if fresh, otherwise runs analysis immediately.
    """
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        return {"status": "error", "message": "No products found"}

    sb = get_supabase_client()
    client_marketplace = "UAE"
    try:
        client_resp = sb.table("pb_clients").select("marketplace").eq("client_id", account_id).execute()
        if client_resp.data:
            client_marketplace = client_resp.data[0].get("marketplace", "UAE")
    except Exception as e:
        print(f"Warning: Failed to fetch client marketplace: {e}")

    mp_name = "KSA" if client_marketplace == "KSA" else "UAE"

    cached_results = []
    seen_parents: set[str] = set()
    for p in products_data:
        parent_asin = p["parent_asin"]
        if parent_asin in seen_parents:
            continue
        seen_parents.add(parent_asin)
        cached = get_cached_analysis(parent_asin, mp_name)
        if cached:
            cached_results.append(cached)
        if len(cached_results) >= 5:
            break

    if cached_results:
        return {"status": "ok", "source": "database", "results": cached_results}

    result = trigger_background_discovery(account_id)
    return {"status": "completed", "source": "fresh_analysis", "details": result}
