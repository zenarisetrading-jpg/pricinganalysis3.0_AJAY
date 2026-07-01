from typing import Any, Dict, List

def assign_tiers(competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Assigns a price tier to each competitor based on quartile split of brand median prices.
    Matches the existing frontend logic for tier classification.
    """
    if not competitors:
        return []

    # Group competitors by brand to find median price per brand
    brand_prices = {}
    for c in competitors:
        brand = c.get("brand")
        if not brand or str(brand).strip().lower() in ["none", "null", ""]:
            brand_key = "UNKNOWN BRAND"
        else:
            brand_key = str(brand).strip().upper()
        
        price = c.get("floor_price") or c.get("price")
        if price is None:
            continue
        try:
            price = float(price)
        except ValueError:
            continue
            
        if brand_key not in brand_prices:
            brand_prices[brand_key] = []
        brand_prices[brand_key].append(price)

    if not brand_prices:
        # Fallback if no valid prices
        for c in competitors:
            c["tier"] = "Unknown"
        return competitors

    # Calculate median price for each brand
    brand_medians = []
    for brand, prices in brand_prices.items():
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        if n % 2 == 1:
            median = sorted_prices[n // 2]
        else:
            median = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2.0
        brand_medians.append(median)

    # Sort brand medians to find quartiles
    sorted_medians = sorted(brand_medians)
    
    import math
    def quartile(arr: List[float], pct: float) -> float:
        if not arr:
            return 0.0
        idx = max(0, math.floor(pct * (len(arr) - 1)))
        return arr[idx]

    q1_price = quartile(sorted_medians, 0.25)
    q2_price = quartile(sorted_medians, 0.50)
    q3_price = quartile(sorted_medians, 0.75)

    def get_tier(price: float) -> str:
        if price <= q1_price:
            return "Entry"
        if price <= q2_price:
            return "Mass"
        if price <= q3_price:
            return "Mid-Premium"
        return "Premium"

    # Assign tier to each competitor
    for c in competitors:
        price = c.get("floor_price") or c.get("price")
        if price is None:
            c["tier"] = "Unknown"
        else:
            try:
                price = float(price)
                c["tier"] = get_tier(price)
            except ValueError:
                c["tier"] = "Unknown"

    return competitors


def filter_competitors_by_tier(competitors: List[Dict[str, Any]], selected_tier: str) -> List[Dict[str, Any]]:
    """
    Calculates tiers and filters the competitor list by the selected tier.
    If selected_tier is 'All' or empty, returns all competitors (still assigning their tiers).
    """
    if not selected_tier or selected_tier.lower() == "all":
        return assign_tiers(competitors)
        
    tiered_competitors = assign_tiers(competitors)
    
    return [c for c in tiered_competitors if c.get("tier", "").lower() == selected_tier.lower()]
