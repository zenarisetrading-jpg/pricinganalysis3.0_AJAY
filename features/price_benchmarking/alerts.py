"""
Threshold-based alert generation for price benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .benchmarking import BenchmarkResult, PriceZone


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    FLOOR_BREACH = "floor_breach"
    CEILING_BREACH = "ceiling_breach"
    COMPETITOR_DROP = "competitor_drop"


@dataclass
class PriceAlert:
    alert_type: AlertType
    severity: AlertSeverity
    sku_id: str
    asin: str
    marketplace: str
    title: str
    your_price: float
    currency: str
    message: str
    action_hint: str
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


CURRENCY_MAP = {
    "UAE": "AED",
    "KSA": "SAR",
    "US": "USD",
    "UK": "GBP",
}


def generate_alerts(
    result: BenchmarkResult,
    previous_snapshot: Optional[BenchmarkResult] = None,
) -> list[PriceAlert]:
    alerts: list[PriceAlert] = []
    cur = CURRENCY_MAP.get(result.marketplace, "")

    if result.zone == PriceZone.BELOW_MARKET:
        alerts.append(
            PriceAlert(
                alert_type=AlertType.FLOOR_BREACH,
                severity=AlertSeverity.HIGH,
                sku_id=result.sku_id,
                asin=result.asin,
                marketplace=result.marketplace,
                title=f"Price below market floor - {result.sku_id}",
                your_price=result.your_price,
                currency=cur,
                message=(
                    f"Your price {cur}{result.your_price:.2f} is below the market floor "
                    f"({cur}{result.floor:.2f})."
                ),
                action_hint=f"Review floor and margin. Raise toward {cur}{result.floor:.2f}.",
                metadata={"floor": result.floor, "gap": result.gap_to_floor},
            )
        )
    elif result.zone == PriceZone.ABOVE_MARKET:
        alerts.append(
            PriceAlert(
                alert_type=AlertType.CEILING_BREACH,
                severity=AlertSeverity.HIGH,
                sku_id=result.sku_id,
                asin=result.asin,
                marketplace=result.marketplace,
                title=f"Price above market ceiling - {result.sku_id}",
                your_price=result.your_price,
                currency=cur,
                message=(
                    f"Your price {cur}{result.your_price:.2f} exceeds the market ceiling "
                    f"({cur}{result.ceiling:.2f})."
                ),
                action_hint=f"Consider reducing price toward {cur}{result.ceiling:.2f}.",
                metadata={"ceiling": result.ceiling, "gap": result.gap_to_ceiling},
            )
        )

    if previous_snapshot and previous_snapshot.floor and result.floor < previous_snapshot.floor:
        alerts.append(
            PriceAlert(
                alert_type=AlertType.COMPETITOR_DROP,
                severity=AlertSeverity.MEDIUM,
                sku_id=result.sku_id,
                asin=result.asin,
                marketplace=result.marketplace,
                title=f"Competitor floor dropped - {result.sku_id}",
                your_price=result.your_price,
                currency=cur,
                message=(
                    f"Market floor moved from {cur}{previous_snapshot.floor:.2f} "
                    f"to {cur}{result.floor:.2f}."
                ),
                action_hint="Review whether to maintain position or react.",
                metadata={
                    "previous_floor": previous_snapshot.floor,
                    "current_floor": result.floor,
                },
            )
        )

    return alerts


def generate_all_alerts(results: list[BenchmarkResult]) -> list[PriceAlert]:
    all_alerts: list[PriceAlert] = []
    for result in results:
        all_alerts.extend(generate_alerts(result))
    return all_alerts
