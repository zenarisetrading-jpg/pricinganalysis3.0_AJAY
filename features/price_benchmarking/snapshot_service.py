"""
Snapshot orchestration — transient analysis and data normalization.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any

from .alerts import generate_alerts
from .benchmarking import CompetitorPrice, compute_benchmark, detect_price_tiers
from .recommendations import RepricingStrategy, recommend


def _clean_price(p) -> float:
    if isinstance(p, (int, float)):
        return float(p)
    if not p:
        return 0.0
    try:
        return float(str(p).replace("AED", "").replace(",", "").strip())
    except Exception:
        return 0.0


def calculate_transient_upload_analysis(
    *,
    client_id: str,
    products: list[dict[str, Any]],
    competitor_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run a pricing analysis using only the provided product and competitor data.
    Does not read from or write to Supabase — callers handle persistence.
    """
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    run_day_iso = date.today().isoformat()

    normalized_products = [_normalize_uploaded_product(p) for p in products]
    normalized_products = [p for p in normalized_products if p is not None]
    normalized_products = _resolve_majority_categories(normalized_products)
    normalized_competitors_raw = [_normalize_uploaded_competitor(c) for c in competitor_records]
    _seen_comp_asins = set()
    normalized_competitors = []
    for c in normalized_competitors_raw:
        if c is not None and c["asin"] not in _seen_comp_asins:
            _seen_comp_asins.add(c["asin"])
            normalized_competitors.append(c)

    snapshot_rows = []
    alert_rows = []
    recommendation_rows = []

    own_asins = {p["asin"] for p in normalized_products}
    for product in normalized_products:
        matching_competitors = [
            c for c in normalized_competitors
            if c["asin"] not in own_asins and _same_uploaded_category(product, c)
        ]

        competitive_tier = product.get("competitive_tier")
        applied_tier: str | None = None  # recorded in recommendation metadata

        if matching_competitors:
            tier_prices = [
                _clean_price(c.get("competitor_price") or c.get("price"))
                for c in matching_competitors
            ]
            tier_prices = [p for p in tier_prices if p > 0]

            if tier_prices:
                tiers = detect_price_tiers(tier_prices)

                if competitive_tier:
                    # Manual override: use the user-chosen tier
                    matched_tier = next(
                        (t for t in tiers if t.label.lower() == competitive_tier.lower()),
                        None,
                    )
                else:
                    # Auto: find which natural tier the product's own price falls into
                    product_price = _clean_price(product.get("price") or 0)
                    matched_tier = None
                    if product_price > 0 and len(tiers) > 1:
                        matched_tier = next(
                            (t for t in tiers if t.min_price <= product_price <= t.max_price),
                            None,
                        )

                if matched_tier and matched_tier.count >= 2:
                    tier_filtered = [
                        c for c in matching_competitors
                        if matched_tier.min_price
                        <= _clean_price(c.get("competitor_price") or c.get("price"))
                        <= matched_tier.max_price
                    ]
                    if tier_filtered:
                        matching_competitors = tier_filtered
                        applied_tier = matched_tier.label

        competitors = [
            CompetitorPrice(
                asin=c["asin"],
                title=c.get("title") or c["asin"],
                price=_clean_price(c.get("competitor_price") or c.get("price")),
                is_fba=c.get("is_buy_box_winner", False),
                brand=c.get("brand"),
                rating=c.get("rating"),
                reviews=int(c["reviews"]) if c.get("reviews") is not None else None,
            )
            for c in matching_competitors
            if _clean_price(c.get("competitor_price") or c.get("price")) > 0
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

        snapshot_rows.append({
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
        })

        for alert in generate_alerts(benchmark):
            alert_rows.append({
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
            })

        strategy = product["strategy"]
        if strategy not in {s.value for s in RepricingStrategy}:
            strategy = RepricingStrategy.MID.value

        recommendation = recommend(
            benchmark,
            strategy=RepricingStrategy(strategy),
            min_price=product.get("min_price"),
            max_price=product.get("max_price"),
            reference_name=product.get("reference_name"),
            applied_tier=applied_tier,
            tier_mode="manual" if competitive_tier else ("auto" if applied_tier else "unfiltered"),
        )
        recommendation_rows.append({
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
        })

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
    Resolve conflicting category assignments across child ASINs sharing a parent_asin.
    Overwrites all children in a group with the majority category.
    """
    parent_groups: dict[str, list] = defaultdict(list)
    for p in products:
        parent = p.get("parent_asin")
        if parent and isinstance(parent, str) and parent.strip():
            parent_groups[parent.strip()].append(p)

    for parent, group in parent_groups.items():
        if len(group) <= 1:
            continue

        name_counts: Counter = Counter()
        name_to_info: dict = {}
        for p in group:
            name = p.get("category_name")
            if name and isinstance(name, str) and name.strip():
                norm = name.strip().lower()
                name_counts[norm] += 1
                if norm not in name_to_info:
                    name_to_info[norm] = {
                        "category_name": name,
                        "category_id": p.get("category_id"),
                        "category_ids": p.get("category_ids"),
                    }

        id_counts: Counter = Counter()
        id_to_info: dict = {}
        if not name_counts:
            for p in group:
                cat_id = p.get("category_id")
                if cat_id is not None and str(cat_id).strip():
                    norm = str(cat_id).strip()
                    id_counts[norm] += 1
                    if norm not in id_to_info:
                        id_to_info[norm] = {
                            "category_name": p.get("category_name"),
                            "category_id": p.get("category_id"),
                            "category_ids": p.get("category_ids"),
                        }

        if name_counts:
            max_freq = max(name_counts.values())
            winner_key = sorted(k for k, v in name_counts.items() if v == max_freq)[0]
            winner_info = name_to_info[winner_key]
        elif id_counts:
            max_freq = max(id_counts.values())
            winner_key = sorted(k for k, v in id_counts.items() if v == max_freq)[0]
            winner_info = id_to_info[winner_key]
        else:
            continue

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
        "competitive_tier": _first_text(raw, "competitive_tier"),
        "min_price": _first_float(raw, "min_price"),
        "max_price": _first_float(raw, "max_price"),
        "sales_rank": _first_float(raw, "sales_rank", "bsr_rank", "rank"),
    }


def _normalize_uploaded_competitor(raw: dict[str, Any]) -> dict[str, Any] | None:
    asin = _first_text(raw, "asin", "ASIN", "competitor_asin")
    price = _first_float(
        raw,
        "floor_price", "buy_box_price", "price", "selling_price",
        "amount", "listing_price", "competitor_price",
    )
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
        rows.append({
            "client_id": client_id,
            "marketplace": _first_text(raw, "marketplace") or "UAE",
            "asin": asin,
            "performance_date": _first_text(raw, "performance_date") or run_day_iso,
            "units_ordered": units_value,
            "sessions": sessions_value,
            "acos": acos or 0,
            "cvr": cvr if cvr is not None else (
                (units_value / sessions_value) * 100 if sessions_value else 0
            ),
            "created_at": _first_text(raw, "created_at") or now_iso,
        })
    return rows


def _build_uploaded_category_rows(
    products: list[dict[str, Any]],
    competitor_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for raw in [*products, *competitor_records]:
        category_name = _first_text(raw, "category_name", "category", "bsr_category") or "Uploaded"
        if category_name not in groups:
            groups[category_name] = {"category_name": category_name, "asins": set(), "rank_by_asin": {}}
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
        rows.append({
            "category_name": group["category_name"],
            "asin_count": len(group["asins"]),
            "asins": sorted(group["asins"]),
            "avg_rank": sum(asin_ranks) / len(asin_ranks) if asin_ranks else None,
        })
    return sorted(rows, key=lambda r: r["avg_rank"] if r["avg_rank"] is not None else float("inf"))


def _same_uploaded_category(product: dict[str, Any], competitor: dict[str, Any]) -> bool:
    product_category_ids = {
        str(c)
        for c in (product.get("category_ids") or [])
        if c is not None and str(c).strip()
    }
    competitor_category_id = competitor.get("category_id")
    product_category_id = product.get("category_id")

    if competitor_category_id and product_category_ids:
        same_category = str(competitor_category_id) in product_category_ids
    elif product_category_id and competitor_category_id:
        same_category = str(product_category_id) == str(competitor_category_id)
    else:
        product_cat = (product.get("category_name") or "").strip().lower()
        competitor_cat = (competitor.get("category_name") or "").strip().lower()
        same_category = (product_cat == competitor_cat) if (product_cat and competitor_cat) else True

    return same_category


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
