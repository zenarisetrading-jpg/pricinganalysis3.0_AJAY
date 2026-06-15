"""
Core price position scoring logic.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PriceZone(str, Enum):
    BELOW_MARKET = "below_market"
    BUDGET = "budget"
    VALUE = "value"
    MID_MARKET = "mid_market"
    PREMIUM = "premium"
    ABOVE_MARKET = "above_market"


@dataclass
class CompetitorPrice:
    asin: str
    title: str
    price: float
    is_fba: bool
    brand: Optional[str] = None
    sales_rank: Optional[int] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None



@dataclass
class BenchmarkResult:
    sku_id: str
    asin: str
    marketplace: str
    your_price: float
    currency: str
    n_competitors: int
    floor: float
    ceiling: float
    median: float
    p25: float
    p75: float
    mean: float
    percentile_rank: float
    zone: PriceZone
    gap_to_floor: float
    gap_to_median: float
    gap_to_ceiling: float
    index_vs_median: float
    competitors: list[CompetitorPrice] = field(default_factory=list)


CURRENCY_MAP = {
    "UAE": "AED",
    "KSA": "SAR",
    "US": "USD",
    "UK": "GBP",
}


def compute_benchmark(
    sku_id: str,
    asin: str,
    your_price: float,
    competitors: list[CompetitorPrice],
    marketplace: str = "UAE",
) -> Optional[BenchmarkResult]:
    prices = [c.price for c in competitors if c.price and c.price > 0]
    n = len(prices)
    
    if n == 0:
        return BenchmarkResult(
            sku_id=sku_id,
            asin=asin,
            marketplace=marketplace,
            your_price=your_price,
            currency=CURRENCY_MAP.get(marketplace, ""),
            n_competitors=0,
            floor=0.0,
            ceiling=0.0,
            median=0.0,
            p25=0.0,
            p75=0.0,
            mean=0.0,
            percentile_rank=0.0,
            zone=PriceZone.MID_MARKET, # Default zone for no competition
            gap_to_floor=0.0,
            gap_to_median=0.0,
            gap_to_ceiling=0.0,
            index_vs_median=0.0,
            competitors=[],
        )

    prices_sorted = sorted(prices)
    floor = prices_sorted[0]
    ceiling = prices_sorted[-1]
    median = statistics.median(prices_sorted)
    mean = statistics.mean(prices_sorted)
    
    # If we have 1 or 2 competitors, p25/p75 won't be very meaningful but we can calculate them
    p25 = _percentile(prices_sorted, 25)
    p75 = _percentile(prices_sorted, 75)
    
    cheaper_count = sum(1 for p in prices if p < your_price)
    percentile_rank = (cheaper_count / n) * 100
    zone = _classify_zone(your_price, floor, ceiling, p25, median, p75)

    return BenchmarkResult(
        sku_id=sku_id,
        asin=asin,
        marketplace=marketplace,
        your_price=your_price,
        currency=CURRENCY_MAP.get(marketplace, ""),
        n_competitors=n,
        floor=floor,
        ceiling=ceiling,
        median=median,
        p25=p25,
        p75=p75,
        mean=mean,
        percentile_rank=percentile_rank,
        zone=zone,
        gap_to_floor=round(your_price - floor, 2),
        gap_to_median=round(your_price - median, 2),
        gap_to_ceiling=round(your_price - ceiling, 2),
        index_vs_median=round((your_price / median) * 100, 1) if median else 0,
        competitors=competitors,
    )


def _percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = (pct / 100) * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


def _classify_zone(
    price: float,
    floor: float,
    ceiling: float,
    p25: float,
    median: float,
    p75: float,
) -> PriceZone:
    if price < floor:
        return PriceZone.BELOW_MARKET
    if price > ceiling:
        return PriceZone.ABOVE_MARKET
    if price <= p25:
        return PriceZone.BUDGET
    if price <= median:
        return PriceZone.VALUE
    if price <= p75:
        return PriceZone.MID_MARKET
    return PriceZone.PREMIUM
