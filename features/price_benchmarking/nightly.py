"""
Nightly aggregation and retention jobs.
"""

import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def aggregate_daily(supabase, target_date: date | None = None) -> dict:
    day = (target_date or date.today() - timedelta(days=1)).isoformat()
    events_resp = (
        supabase.table("pb_price_events")
        .select("asin, marketplace, floor_price, ceiling_price, median_price, buy_box_price, foep")
        .gte("created_at", f"{day}T00:00:00+00:00")
        .lt("created_at", f"{day}T23:59:59+00:00")
        .execute()
    )
    events = events_resp.data or []
    if not events:
        logger.info("No events for %s to aggregate", day)
        return {"date": day, "n_asins": 0}

    groups = defaultdict(list)
    for event in events:
        groups[(event["asin"], event["marketplace"])].append(event)

    rows = []
    for (asin, marketplace), group in groups.items():
        floors = [e["floor_price"] for e in group if e.get("floor_price") is not None]
        ceilings = [e["ceiling_price"] for e in group if e.get("ceiling_price") is not None]
        medians = [e["median_price"] for e in group if e.get("median_price") is not None]
        buy_boxes = [e["buy_box_price"] for e in group if e.get("buy_box_price") is not None]
        foeps = [e["foep"] for e in group if e.get("foep") is not None]
        all_prices = floors + medians

        rows.append(
            {
                "asin": asin,
                "marketplace": marketplace,
                "snapshot_date": day,
                "n_events": len(group),
                "floor_price": min(floors) if floors else None,
                "ceiling_price": max(ceilings) if ceilings else None,
                "median_price": statistics.median(medians) if medians else None,
                "mean_price": sum(all_prices) / len(all_prices) if all_prices else None,
                "p25_price": _percentile(sorted(all_prices), 25) if all_prices else None,
                "p75_price": _percentile(sorted(all_prices), 75) if all_prices else None,
                "buy_box_price": statistics.median(buy_boxes) if buy_boxes else None,
                "foep": statistics.median(foeps) if foeps else None,
            }
        )

    supabase.table("pb_price_snapshots_daily").upsert(
        rows, on_conflict="asin,marketplace,snapshot_date"
    ).execute()
    return {"date": day, "n_asins": len(rows)}


def purge_old_events(supabase, days: int = 90) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    supabase.table("pb_price_events").delete().lt("created_at", cutoff).execute()
    return {"purged_before": cutoff, "retention_days": days}


def _percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = (pct / 100) * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])
