"""
Repricing recommendation engine with ACoS guard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .benchmarking import BenchmarkResult, PriceZone


class RepricingStrategy(str, Enum):
    VALUE = "value"
    MID = "mid"
    PREMIUM = "premium"
    FLOOR = "floor"
    CUSTOM = "custom"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CURRENCY_MAP = {
    "UAE": "AED",
    "KSA": "SAR",
    "US": "USD",
    "UK": "GBP",
}


@dataclass
class RepricingRecommendation:
    sku_id: str
    asin: str
    marketplace: str
    strategy: RepricingStrategy
    current_price: float
    recommended_price: float
    currency: str
    change_amount: float
    change_pct: float
    action: str
    confidence: ConfidenceLevel
    reasoning: str
    metadata: dict = field(default_factory=dict)


def recommend(
    result: BenchmarkResult,
    strategy: RepricingStrategy = RepricingStrategy.MID,
    custom_target: Optional[float] = None,
    floor_undercut_pct: float = 2.0,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    **kwargs,
) -> RepricingRecommendation:
    cur = CURRENCY_MAP.get(result.marketplace, "")
    reference_name = str(kwargs.get("reference_name") or "").strip()
    if result.n_competitors == 0:
        no_competitor_reason = (
            "0 competitors matched your keyword. Target price calculated as 0."
            if reference_name
            else "0 competitors found in the category pool. Target price calculated as 0."
        )
        return RepricingRecommendation(
            sku_id=result.sku_id,
            asin=result.asin,
            marketplace=result.marketplace,
            strategy=strategy,
            current_price=result.your_price,
            recommended_price=0.0,
            currency=cur,
            change_amount=0.0,
            change_pct=0.0,
            action="hold",
            confidence=ConfidenceLevel.LOW,
            reasoning=no_competitor_reason,
            metadata={
                "zone": result.zone.value,
                "n_competitors": 0,
                **{k: v for k, v in kwargs.items() if v is not None},
            },
        )

    if result.n_competitors < 5:
        confidence = ConfidenceLevel.LOW
    elif result.n_competitors <= 15:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.HIGH

    if strategy == RepricingStrategy.CUSTOM and custom_target:
        target = custom_target
        reasoning_base = f"Custom target price of {cur}{custom_target:.2f} applied."
    elif strategy == RepricingStrategy.VALUE:
        target = (result.floor + result.p25) / 2
        reasoning_base = (
            f"Value strategy: midpoint of floor ({cur}{result.floor:.2f}) and "
            f"p25 ({cur}{result.p25:.2f})."
        )
    elif strategy == RepricingStrategy.MID:
        target = result.median
        reasoning_base = (
            f"Mid-market strategy: median ({cur}{result.median:.2f})."
        )
    elif strategy == RepricingStrategy.PREMIUM:
        target = (result.p75 + result.ceiling) / 2
        reasoning_base = (
            f"Premium strategy: midpoint of p75 ({cur}{result.p75:.2f}) and "
            f"ceiling ({cur}{result.ceiling:.2f})."
        )
    elif strategy == RepricingStrategy.FLOOR:
        target = result.floor * (1 - floor_undercut_pct / 100)
        reasoning_base = (
            f"Floor strategy: undercut floor ({cur}{result.floor:.2f}) by "
            f"{floor_undercut_pct}%."
        )
    else:
        target = result.median
        reasoning_base = f"Defaulting to market median {cur}{result.median:.2f}."

    if min_price and target < min_price:
        target = min_price
        reasoning_base += f" Floored at {cur}{min_price:.2f}."
    if max_price and target > max_price:
        target = max_price
        reasoning_base += f" Capped at {cur}{max_price:.2f}."

    target = round(target, 2)
    change_amount = round(target - result.your_price, 2)
    change_pct = round((change_amount / result.your_price) * 100, 2) if result.your_price else 0

    # Calculate action against median for all tiers
    median_change = result.median - result.your_price
    median_change_pct = (median_change / result.your_price) * 100 if result.your_price else 0

    if abs(median_change_pct) < 1.0:
        action = "hold"
    elif median_change > 0:
        action = "increase"
    else:
        action = "decrease"

    avg_acos = kwargs.get("avg_acos")
    if action == "decrease" and avg_acos and avg_acos > 35:
        action = "hold"
        reasoning_base += (
            f" Price cut suppressed because ACoS is {avg_acos:.1f}% and margin "
            "pressure is already high."
        )

    full_reasoning = " | ".join(
        filter(
            None,
            [
                (
                    f"{result.n_competitors} competitors. Range {cur}{result.floor:.2f}-"
                    f"{cur}{result.ceiling:.2f}. Median {cur}{result.median:.2f}."
                ),
                _zone_reasoning(result.zone),
                reasoning_base,
            ],
        )
    )

    return RepricingRecommendation(
        sku_id=result.sku_id,
        asin=result.asin,
        marketplace=result.marketplace,
        strategy=strategy,
        current_price=result.your_price,
        recommended_price=target,
        currency=cur,
        change_amount=change_amount,
        change_pct=change_pct,
        action=action,
        confidence=confidence,
        reasoning=full_reasoning,
        metadata={
            "zone": result.zone.value,
            "percentile_rank": result.percentile_rank,
            "index_vs_median": result.index_vs_median,
            "n_competitors": result.n_competitors,
            "floor_price": result.floor,
            "ceiling_price": result.ceiling,
            "competitors": [c.__dict__ for c in result.competitors],
            **{k: v for k, v in kwargs.items() if v is not None},
        },
    )


def recommend_portfolio(
    results: list[BenchmarkResult],
    default_strategy: RepricingStrategy = RepricingStrategy.MID,
    strategy_overrides: Optional[dict[str, RepricingStrategy]] = None,
    min_prices: Optional[dict[str, float]] = None,
    max_prices: Optional[dict[str, float]] = None,
    performance_data: Optional[dict[str, dict]] = None,
) -> list[RepricingRecommendation]:
    recs = []
    for result in results:
        strategy = (strategy_overrides or {}).get(result.asin, default_strategy)
        min_p = (min_prices or {}).get(result.asin)
        max_p = (max_prices or {}).get(result.asin)
        perf = (performance_data or {}).get(result.asin, {})
        recs.append(recommend(result, strategy=strategy, min_price=min_p, max_price=max_p, **perf))
    recs.sort(key=lambda rec: (rec.action == "hold", -abs(rec.change_pct)))
    return recs


def _zone_reasoning(zone: PriceZone) -> str:
    zone_messages = {
        PriceZone.BELOW_MARKET: "Currently below market floor.",
        PriceZone.BUDGET: "Currently in budget zone.",
        PriceZone.VALUE: "Currently in value zone.",
        PriceZone.MID_MARKET: "Currently in mid-market zone.",
        PriceZone.PREMIUM: "Currently in premium zone.",
        PriceZone.ABOVE_MARKET: "Currently above market ceiling.",
    }
    return zone_messages.get(zone, "")
