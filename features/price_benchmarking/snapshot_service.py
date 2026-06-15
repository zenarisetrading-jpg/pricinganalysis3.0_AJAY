"""
Snapshot orchestration for the standalone price benchmarking module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .alerts import generate_alerts
from .benchmarking import BenchmarkResult, CompetitorPrice, compute_benchmark
from .recommendations import RepricingStrategy, recommend
from .relevance_filter import is_related


@dataclass
class PreviousSnapshot:
    asin: str
    sku_id: str
    your_price: float
    floor: float
    ceiling: float
    median: float
    p25: float
    p75: float
    marketplace: str


def calculate_benchmarks_for_client(
    *,
    supabase,
    client_id: str,
    marketplace: str,
    snapshot_date: date | None = None,
    market_prices_override: dict[str, dict] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Computes benchmarks and recommendations for a client based on 
    the latest data in Tier 1 (pb_price_events).
    """
    run_day = snapshot_date or date.today()
    run_day_iso = run_day.isoformat()
    
    skus = _load_skus(supabase, client_id)
    if not skus:
        return {"status": "no_skus", "n_asins": 0}

    # If in simulation mode with overrides, filter to ONLY those ASINs in the override
    if market_prices_override:
        skus = [s for s in skus if s["asin"] in market_prices_override]
        if not skus:
            return {"status": "no_matches", "n_asins": 0}

    own_listings = _load_listings(supabase, client_id, marketplace)
    performance = _load_latest_performance(supabase, client_id, marketplace)
    
    # Load child -> parent mapping from SADDL DB
    child_to_parent = {}
    try:
        from .saddl_db import fetch_account_products_with_categories
        saddl_products = fetch_account_products_with_categories(client_id)
        child_to_parent = {
            p["asin"]: p["parent_asin"]
            for p in saddl_products
            if p.get("asin") and p.get("parent_asin")
        }
    except Exception as e:
        print(f"Warning: Failed to fetch child-to-parent mapping in snapshot calculation: {e}")
    
    # Load the latest market prices for all relevant ASINs
    if market_prices_override:
        market_prices = market_prices_override
    else:
        market_prices = _load_latest_tier1_prices(supabase, marketplace)
    
    # Load previous snapshots for historical comparison
    previous = _load_previous_snapshots(supabase, client_id, run_day)

    client_snapshot_rows = []
    alert_rows = []
    recommendation_rows = []
    own_asins = {s["asin"] for s in skus}

    for sku in skus:
        listing = own_listings.get(sku["asin"], {})
        your_price = listing.get("price")
        if your_price is None:
            your_price = sku.get("fallback_price")
        if your_price is None:
            continue

        # Get competitors for this SKU
        competitor_map = _get_effective_competitors(supabase, client_id, sku.get("category_id"), marketplace)
        
        # Build competitor list from Tier 1 prices
        competitors = []
        ref_name = listing.get("reference_name")
        exclude_kws = listing.get("exclude_keywords")
        
        for c_asin, comp_info in competitor_map.items():
            if c_asin in own_asins:
                continue
            c_title = comp_info.get("title") or c_asin
            c_brand = comp_info.get("brand")
            price_data = market_prices.get(c_asin)
            if price_data:
                # Apply Relevance Filtering if reference_name or exclude_keywords is set
                if ref_name or exclude_kws:
                    candidate = {
                        "asin": c_asin,
                        "title": c_title,
                        "brand": c_brand,
                    }
                    target = {
                        "asin": sku["asin"],
                        "reference_name": ref_name,
                        "exclude_keywords": exclude_kws
                    }
                    if not is_related(target, candidate):
                        continue

                competitors.append(
                    CompetitorPrice(
                        asin=c_asin,
                        title=c_title,
                        price=float(price_data["price"]),
                        is_fba=price_data.get("is_buy_box_winner", False),
                        brand=c_brand or price_data.get("brand"),
                        rating=price_data.get("rating"),
                        reviews=int(price_data["reviews"]) if price_data.get("reviews") is not None else None,
                    )
                )

        benchmark = compute_benchmark(
            sku_id=sku["sku_id"],
            asin=sku["asin"],
            your_price=float(your_price),
            competitors=competitors,
            marketplace=marketplace,
        )
        if not benchmark:
            continue

        client_snapshot_rows.append(
            {
                "client_id": client_id,
                "sku_id": sku["sku_id"],
                "asin": sku["asin"],
                "parent_asin": child_to_parent.get(sku["asin"]) or sku["asin"],
                "snapshot_date": run_day_iso,
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
                "strategy": sku["strategy"],
            }
        )

        previous_benchmark = _to_previous_benchmark(previous.get(sku["asin"]))
        for alert in generate_alerts(benchmark, previous_benchmark):
            alert_rows.append(
                {
                    "client_id": client_id,
                    "asin": sku["asin"],
                    "sku_id": sku["sku_id"],
                    "parent_asin": child_to_parent.get(sku["asin"]) or sku["asin"],
                    "marketplace": marketplace,
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "action_hint": alert.action_hint,
                    "metadata": alert.metadata,
                }
            )

        perf = performance.get(sku["asin"], {})
        recommendation = recommend(
            benchmark,
            strategy=RepricingStrategy(sku["strategy"]),
            min_price=sku.get("min_price"),
            max_price=sku.get("max_price"),
            reference_name=ref_name,
            **perf,
        )
        recommendation_rows.append(
            {
                "client_id": client_id,
                "asin": sku["asin"],
                "sku_id": sku["sku_id"],
                "parent_asin": child_to_parent.get(sku["asin"]) or sku["asin"],
                "marketplace": marketplace,
                "strategy": recommendation.strategy.value,
                "current_price": recommendation.current_price,
                "recommended_price": recommendation.recommended_price,
                "change_amount": recommendation.change_amount,
                "change_pct": recommendation.change_pct,
                "action": recommendation.action,
                "confidence": recommendation.confidence.value,
                "reasoning": recommendation.reasoning,
                "metadata": recommendation.metadata,
                "snapshot_date": run_day_iso,
            }
        )

    if persist:
        if client_snapshot_rows:
            supabase.table("pb_client_snapshots_daily").upsert(
                client_snapshot_rows,
                on_conflict="client_id,asin,snapshot_date",
            ).execute()
        if alert_rows:
            supabase.table("pb_alerts").insert(alert_rows).execute()
        if recommendation_rows:
            supabase.table("pb_recommendations").insert(recommendation_rows).execute()

        _insert_run(
            supabase,
            {
                "run_type": "snapshot",
                "client_id": client_id,
                "marketplace": marketplace,
                "run_date": run_day_iso,
                "n_asins": len(client_snapshot_rows),
                "n_alerts": len(alert_rows),
                "n_recommendations": len(recommendation_rows),
                "status": "ok",
            },
        )
    
    return {
        "status": "ok",
        "n_asins": len(client_snapshot_rows),
        "n_alerts": len(alert_rows),
        "n_recommendations": len(recommendation_rows),
        "snapshots": client_snapshot_rows,
        "alerts": alert_rows,
        "recommendations": recommendation_rows,
    }


def _load_skus(supabase, client_id: str) -> list[dict]:
    return (
        supabase.table("pb_benchmarking_skus")
        .select("*")
        .eq("client_id", client_id)
        .eq("is_active", True)
        .order("sku_id")
        .execute()
        .data
        or []
    )


def _load_listings(supabase, client_id: str, marketplace: str) -> dict[str, dict]:
    rows = (
        supabase.table("pb_client_listings")
        .select("asin, listing_price, price, reference_name, exclude_keywords")
        .eq("client_id", client_id)
        .eq("marketplace", marketplace)
        .execute()
        .data
        or []
    )
    listings = {}
    for row in rows:
        value = row.get("listing_price") or row.get("price")
        if value is not None:
            listings[row["asin"]] = {
                "price": float(value),
                "reference_name": row.get("reference_name"),
                "exclude_keywords": row.get("exclude_keywords")
            }
    return listings


def _load_latest_performance(supabase, client_id: str, marketplace: str) -> dict[str, dict]:
    rows = (
        supabase.table("pb_client_performance_daily")
        .select("asin, units_ordered, sessions, acos, cvr, performance_date")
        .eq("client_id", client_id)
        .eq("marketplace", marketplace)
        .order("performance_date", desc=True)
        .execute()
        .data
        or []
    )
    perf = {}
    for row in rows:
        asin = row["asin"]
        if asin in perf:
            continue
        perf[asin] = {
            "avg_acos": float(row["acos"]) if row.get("acos") is not None else None,
            "units_30d": row.get("units_ordered"),
            "sessions_30d": row.get("sessions"),
            "cvr": float(row["cvr"]) if row.get("cvr") is not None else None,
        }
    return perf


def _get_effective_competitors(supabase, client_id: str, category_id: int | None, marketplace: str) -> dict[str, dict[str, Any]]:
    if not category_id:
        return {}
    pool_resp = (
        supabase.table("pb_category_competitors")
        .select("asin, title, brand")
        .eq("category_id", category_id)
        .eq("marketplace", marketplace)
        .eq("is_active", True)
        .execute()
    )
    pool_asins = {
        row["asin"]: {
            "title": row.get("title") or row["asin"],
            "brand": row.get("brand")
        }
        for row in (pool_resp.data or [])
    }
    overrides_resp = (
        supabase.table("pb_client_competitor_overrides")
        .select("asin, action")
        .eq("client_id", client_id)
        .execute()
    )
    for override in overrides_resp.data or []:
        if override["action"] == "exclude":
            pool_asins.pop(override["asin"], None)
        elif override["action"] == "include" and override["asin"] not in pool_asins:
            pool_asins[override["asin"]] = {
                "title": override["asin"],
                "brand": None
            }
    return pool_asins


def _load_latest_tier1_prices(supabase, marketplace: str) -> dict[str, dict]:
    """
    Loads the most recent price event for every ASIN in a marketplace.
    """
    # Simple approach: load all events from the last 48h and keep the latest per ASIN
    cutoff = (date.today() - timedelta(days=2)).isoformat()
    resp = supabase.table("pb_price_events")\
        .select("asin, floor_price, is_buy_box_winner, rating, reviews, brand, created_at")\
        .eq("marketplace", marketplace)\
        .gte("created_at", cutoff)\
        .order("created_at", desc=True)\
        .execute()
    
    events = resp.data or []
    latest = {}
    for ev in events:
        asin = ev["asin"]
        if asin not in latest:
            latest[asin] = {
                "price": ev["floor_price"],
                "is_buy_box_winner": ev.get("is_buy_box_winner", False),
                "rating": ev.get("rating"),
                "reviews": ev.get("reviews"),
                "brand": ev.get("brand")
            }
    return latest


def _build_competitor_prices(
    competitor_asins: list[str],
    snapshots: dict[str, LiveOfferSnapshot],
) -> list[CompetitorPrice]:
    competitors = []
    for competitor_asin in competitor_asins:
        snapshot = snapshots.get(competitor_asin)
        if not snapshot:
            continue
        price = snapshot.buy_box_price or snapshot.floor_price or snapshot.median_price
        if price is None:
            continue
        competitors.append(
            CompetitorPrice(
                asin=competitor_asin,
                title=competitor_asin,
                price=float(price),
                is_fba=bool(snapshot.buy_box_is_fba),
            )
        )
    return competitors


def _load_previous_snapshots(supabase, client_id: str, run_day: date) -> dict[str, PreviousSnapshot]:
    prev_day = (run_day - timedelta(days=1)).isoformat()
    rows = (
        supabase.table("pb_client_snapshots_daily")
        .select("*")
        .eq("client_id", client_id)
        .eq("snapshot_date", prev_day)
        .execute()
        .data
        or []
    )
    return {
        row["asin"]: PreviousSnapshot(
            asin=row["asin"],
            sku_id=row["sku_id"],
            your_price=float(row["your_price"]),
            floor=float(row["floor_price"]),
            ceiling=float(row["ceiling_price"]),
            median=float(row["median_price"]),
            p25=float(row["p25_price"]),
            p75=float(row["p75_price"]),
            marketplace="UAE",
        )
        for row in rows
        if all(row.get(key) is not None for key in ("your_price", "floor_price", "ceiling_price", "median_price", "p25_price", "p75_price"))
    }


def _to_previous_benchmark(previous: PreviousSnapshot | None) -> BenchmarkResult | None:
    if previous is None:
        return None
    return BenchmarkResult(
        sku_id=previous.sku_id,
        asin=previous.asin,
        marketplace=previous.marketplace,
        your_price=previous.your_price,
        currency="",
        n_competitors=3,
        floor=previous.floor,
        ceiling=previous.ceiling,
        median=previous.median,
        p25=previous.p25,
        p75=previous.p75,
        mean=previous.median,
        percentile_rank=0.0,
        zone=compute_benchmark(
            sku_id=previous.sku_id,
            asin=previous.asin,
            your_price=previous.your_price,
            competitors=[
                CompetitorPrice(asin="a", title="a", price=previous.floor, is_fba=False),
                CompetitorPrice(asin="b", title="b", price=previous.median, is_fba=False),
                CompetitorPrice(asin="c", title="c", price=previous.ceiling, is_fba=False),
            ],
            marketplace=previous.marketplace,
        ).zone,
        gap_to_floor=previous.your_price - previous.floor,
        gap_to_median=previous.your_price - previous.median,
        gap_to_ceiling=previous.your_price - previous.ceiling,
        index_vs_median=(previous.your_price / previous.median) * 100 if previous.median else 0,
        competitors=[],
    )



def calculate_transient_upload_analysis(
    *,
    client_id: str,
    products: list[dict[str, Any]],
    competitor_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run a pricing test using only the uploaded product and competitor files.

    This helper must not call Supabase. It is used by dashboard simulation mode
    so old database rows cannot influence the analysis or display.
    """
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    run_day_iso = date.today().isoformat()

    normalized_products = [_normalize_uploaded_product(p) for p in products]
    normalized_products = [p for p in normalized_products if p is not None]
    normalized_products = _resolve_majority_categories(normalized_products)
    normalized_competitors = [_normalize_uploaded_competitor(c) for c in competitor_records]
    normalized_competitors = [c for c in normalized_competitors if c is not None]

    snapshot_rows = []
    alert_rows = []
    recommendation_rows = []

    own_asins = {p["asin"] for p in normalized_products}
    for product in normalized_products:
        matching_competitors = [
            c for c in normalized_competitors
            if c["asin"] not in own_asins and _same_uploaded_category(product, c)
        ]
        
        print(f"      DEBUG: Found {len(matching_competitors)} matching competitors for {product['asin']}")
        def clean_price(p):
            if isinstance(p, (int, float)): return float(p)
            if not p: return 0.0
            try:
                # Remove currency symbols and commas
                clean = str(p).replace("AED", "").replace(",", "").strip()
                return float(clean)
            except:
                return 0.0

        competitors = [
            CompetitorPrice(
                asin=c["asin"],
                title=c.get("title") or c["asin"],
                price=clean_price(c.get("competitor_price") or c.get("price")),
                is_fba=c.get("is_buy_box_winner", False),
                brand=c.get("brand"),
                rating=c.get("rating"),
                reviews=int(c["reviews"]) if c.get("reviews") is not None else None,
            )
            for c in matching_competitors if clean_price(c.get("competitor_price") or c.get("price")) > 0
        ]

        benchmark = compute_benchmark(
            sku_id=product["sku_id"],
            asin=product["asin"],
            your_price=product["price"],
            competitors=competitors,
            marketplace=product["marketplace"],
        )
        if not benchmark:
            continue

        snapshot_rows.append(
            {
                "client_id": client_id,
                "sku_id": product["sku_id"],
                "asin": product["asin"],
                "parent_asin": product.get("parent_asin") or product["asin"],
                "snapshot_date": run_day_iso,
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
                "strategy": product["strategy"],
            }
        )

        for alert in generate_alerts(benchmark):
            alert_rows.append(
                {
                    "client_id": client_id,
                    "asin": product["asin"],
                    "sku_id": product["sku_id"],
                    "parent_asin": product.get("parent_asin") or product["asin"],
                    "marketplace": product["marketplace"],
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "action_hint": alert.action_hint,
                    "metadata": alert.metadata,
                    "created_at": now_iso,
                }
            )

        strategy = product["strategy"]
        if strategy not in {s.value for s in RepricingStrategy}:
            strategy = RepricingStrategy.MID.value

        recommendation = recommend(
            benchmark,
            strategy=RepricingStrategy(strategy),
            min_price=product.get("min_price"),
            max_price=product.get("max_price"),
            reference_name=product.get("reference_name"),
        )
        recommendation_rows.append(
            {
                "client_id": client_id,
                "asin": product["asin"],
                "sku_id": product["sku_id"],
                "parent_asin": product.get("parent_asin") or product["asin"],
                "marketplace": product["marketplace"],
                "strategy": recommendation.strategy.value,
                "current_price": recommendation.current_price,
                "recommended_price": recommendation.recommended_price,
                "change_amount": recommendation.change_amount,
                "change_pct": recommendation.change_pct,
                "action": recommendation.action,
                "confidence": recommendation.confidence.value,
                "reasoning": recommendation.reasoning,
                "metadata": recommendation.metadata,
                "snapshot_date": run_day_iso,
                "created_at": now_iso,
            }
        )

    return {
        "status": "ok",
        "source": "uploaded_files_only",
        "n_uploaded_products": len(normalized_products),
        "n_uploaded_competitors": len(normalized_competitors),
        "n_asins": len(snapshot_rows),
        "n_alerts": len(alert_rows),
        "n_recommendations": len(recommendation_rows),
        "snapshots": snapshot_rows,
        "alerts": alert_rows,
        "recommendations": recommendation_rows,
        "performance": _build_uploaded_performance_rows(client_id, products, now_iso, run_day_iso),
        "categories": _build_uploaded_category_rows(normalized_products, competitor_records),
        "competitors": normalized_competitors,
        "products": normalized_products,
    }



def _resolve_majority_categories(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Resolves conflicting category assignments across child ASINs that belong to the same parent_asin.
    Overwrites the category_name, category_id, and category_ids of all child ASINs in a group
    with the majority category's details. If there is a tie, defaults to alphabetical fallback.
    """
    from collections import Counter, defaultdict

    # 1. Group products by parent_asin
    parent_groups = defaultdict(list)
    for p in products:
        parent = p.get("parent_asin")
        if parent and isinstance(parent, str) and parent.strip():
            parent_groups[parent.strip()].append(p)

    for parent, group in parent_groups.items():
        if len(group) <= 1:
            continue

        # Count frequencies of category names
        name_counts = Counter()
        name_to_info = {}

        for p in group:
            name = p.get("category_name")
            if name and isinstance(name, str) and name.strip():
                norm_name = name.strip().lower()
                name_counts[norm_name] += 1
                if norm_name not in name_to_info:
                    name_to_info[norm_name] = {
                        "category_name": name,
                        "category_id": p.get("category_id"),
                        "category_ids": p.get("category_ids"),
                    }

        id_counts = Counter()
        id_to_info = {}

        # Fallback to category_id if category_name is completely missing for all products
        if not name_counts:
            for p in group:
                cat_id = p.get("category_id")
                if cat_id is not None and str(cat_id).strip():
                    norm_id = str(cat_id).strip()
                    id_counts[norm_id] += 1
                    if norm_id not in id_to_info:
                        id_to_info[norm_id] = {
                            "category_name": p.get("category_name"),
                            "category_id": p.get("category_id"),
                            "category_ids": p.get("category_ids"),
                        }

        # Determine winner info
        if name_counts:
            max_freq = max(name_counts.values())
            candidates = [k for k, v in name_counts.items() if v == max_freq]
            candidates.sort() # Alphabetical sorting
            winner_key = candidates[0]
            winner_info = name_to_info[winner_key]
        elif id_counts:
            max_freq = max(id_counts.values())
            candidates = [k for k, v in id_counts.items() if v == max_freq]
            candidates.sort() # Alphabetical sorting
            winner_key = candidates[0]
            winner_info = id_to_info[winner_key]
        else:
            # No category info at all in this parent group, leave untouched
            continue

        # Overwrite all child ASINs in the group with the winning category info
        for p in group:
            p["category_name"] = winner_info["category_name"]
            p["category_id"] = winner_info["category_id"]
            p["category_ids"] = winner_info["category_ids"]

    return products


def _normalize_uploaded_product(raw: dict[str, Any]) -> dict[str, Any] | None:
    asin = _first_text(raw, "asin", "ASIN")
    price = _first_float(raw, "listing_price", "price", "selling_price", "floor_price", "buy_box_price", "amount")
    if not asin or price is None:
        return None

    raw_category_ids = raw.get("category_ids") or raw.get("parent_category_ids") or []
    if isinstance(raw_category_ids, (str, int, float)):
        raw_category_ids = [raw_category_ids]
    category_ids = [str(c).strip() for c in raw_category_ids if str(c).strip()]
    category_id = _first_text(raw, "category_id")
    if category_id and category_id not in category_ids:
        category_ids.append(category_id)

    sku_id = _first_text(raw, "sku_id", "sku", "SKU") or asin
    return {
        "asin": asin,
        "sku_id": sku_id,
        "price": price,
        "marketplace": _first_text(raw, "marketplace") or "UAE",
        "category_id": category_id,
        "category_ids": category_ids,
        "category_name": _first_text(raw, "category_name", "category", "bsr_category"),
        "parent_asin": _first_text(raw, "parent_asin"),
        "reference_name": _first_text(raw, "reference_name"),
        "title": _first_text(raw, "title", "name", "product_title"),
        "strategy": _first_text(raw, "strategy") or RepricingStrategy.MID.value,
        "min_price": _first_float(raw, "min_price"),
        "max_price": _first_float(raw, "max_price"),
        "sales_rank": _first_float(raw, "sales_rank", "bsr_rank", "rank"),
    }


def _normalize_uploaded_competitor(raw: dict[str, Any]) -> dict[str, Any] | None:
    asin = _first_text(raw, "asin", "ASIN", "competitor_asin")
    price = _first_float(raw, "floor_price", "buy_box_price", "price", "selling_price", "amount", "listing_price", "competitor_price")
    if not asin or price is None:
        return None

    return {
        "asin": asin,
        "title": _first_text(raw, "title", "name", "product_title", "competitor_title"),
        "price": price,
        "brand": _first_text(raw, "brand", "brand_name", "competitor_brand"),
        "marketplace": _first_text(raw, "marketplace") or "UAE",
        "category_id": _first_text(raw, "category_id"),
        "category_name": _first_text(raw, "category_name", "category", "bsr_category"),
        "sales_rank": _first_float(raw, "sales_rank", "bsr_rank", "rank"),
        "is_buy_box_winner": bool(raw.get("is_buy_box_winner", False)),
        "rating": _first_float(raw, "rating", "competitor_rating"),
        "reviews": _first_float(raw, "reviews", "competitor_reviews"),
    }


def _build_uploaded_performance_rows(
    client_id: str,
    products: list[dict[str, Any]],
    now_iso: str,
    run_day_iso: str,
) -> list[dict[str, Any]]:
    rows = []
    for raw in products:
        asin = _first_text(raw, "asin", "ASIN")
        if not asin:
            continue

        units = _first_float(raw, "units_ordered", "orders")
        sessions = _first_float(raw, "sessions")
        acos = _first_float(raw, "acos")
        cvr = _first_float(raw, "cvr")

        if units is None and sessions is None and acos is None and cvr is None:
            continue

        units_value = int(units or 0)
        sessions_value = int(sessions or 0)
        rows.append(
            {
                "client_id": client_id,
                "marketplace": _first_text(raw, "marketplace") or "UAE",
                "asin": asin,
                "performance_date": _first_text(raw, "performance_date") or run_day_iso,
                "units_ordered": units_value,
                "sessions": sessions_value,
                "acos": acos or 0,
                "cvr": cvr if cvr is not None else ((units_value / sessions_value) * 100 if sessions_value else 0),
                "created_at": _first_text(raw, "created_at") or now_iso,
            }
        )
    return rows


def _build_uploaded_category_rows(
    products: list[dict[str, Any]],
    competitor_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for raw in [*products, *competitor_records]:
        category_name = _first_text(raw, "category_name", "category", "bsr_category") or "Uploaded"
        if category_name not in groups:
            groups[category_name] = {
                "category_name": category_name,
                "asins": set(),
                "rank_by_asin": {},
                "rank_total": 0.0,
                "rank_count": 0,
            }

        group = groups[category_name]
        asin = _first_text(raw, "asin", "ASIN")
        if asin:
            group["asins"].add(asin)
        rank = _first_float(raw, "avg_rank", "sales_rank", "bsr_rank", "rank")
        if asin and rank and rank > 0:
            group["rank_by_asin"].setdefault(asin, []).append(rank)

    rows = []
    for group in groups.values():
        asin_ranks = [
            sum(ranks) / len(ranks)
            for ranks in group["rank_by_asin"].values()
            if ranks
        ]
        rows.append(
            {
                "category_name": group["category_name"],
                "asin_count": len(group["asins"]),
                "asins": sorted(group["asins"]),
                "avg_rank": sum(asin_ranks) / len(asin_ranks) if asin_ranks else None,
            }
        )

    return sorted(rows, key=lambda row: row["avg_rank"] if row["avg_rank"] is not None else float("inf"))


def _same_uploaded_category(product: dict[str, Any], competitor: dict[str, Any]) -> bool:
    """
    Check whether a competitor belongs to the same category as the product.

    When competitor records have no category info at all they are already
    assumed to be from the right pool (filtered upstream), so we let them
    through rather than dropping them silently.
    """
    competitor_category_id = competitor.get("category_id")

    # If the competitor carries no category tag at all, allow it through.
    # It was already selected from the correct category pool upstream.
    if not competitor_category_id:
        return True

    product_category_id = product.get("category_id")
    product_category_ids = {
        str(c)
        for c in (product.get("category_ids") or [])
        if c is not None and str(c).strip()
    }

    # Match against the product's category_ids set (supports multi-category parents)
    if product_category_ids:
        return str(competitor_category_id) in product_category_ids

    # Fallback: match against single category_id
    if product_category_id:
        return str(product_category_id) == str(competitor_category_id)

    # Fallback: match by category_name string
    product_category = (product.get("category_name") or "").strip().lower()
    competitor_category = (competitor.get("category_name") or "").strip().lower()
    if product_category and competitor_category:
        return product_category == competitor_category

    # No category info on either side — allow through
    return True



def _first_text(raw: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_float(raw: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, dict):
            value = value.get("value") or value.get("amount") or value.get("price")
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None

def _insert_run(supabase, payload: dict) -> None:
    supabase.table("pb_runs").insert(payload).execute()
