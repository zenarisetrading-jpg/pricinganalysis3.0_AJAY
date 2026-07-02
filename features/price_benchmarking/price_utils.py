from typing import List, Dict, Any

def compute_parent_avg_prices(saddl_products: List[Dict[str, Any]], live_prices: Dict[str, float]) -> Dict[str, float]:
    """
    Given a list of products (with parent-child mappings) and a dict of live prices,
    returns a dictionary mapping parent ASINs to their average active child ASIN selling price.
    """
    # Map child ASINs to their parent ASINs
    child_to_parent = {}
    for p in saddl_products:
        asin = p.get("asin")
        if asin:
            child_to_parent[asin] = p.get("parent_asin") or asin

    # Collect valid prices per parent
    parent_prices_map: Dict[str, List[float]] = {}
    for child_asin, price in live_prices.items():
        if price is not None and price > 0:
            p_asin = child_to_parent.get(child_asin, child_asin)
            parent_prices_map.setdefault(p_asin, []).append(float(price))

    # Calculate averages
    parent_avg_prices: Dict[str, float] = {}
    for p_asin, prices in parent_prices_map.items():
        if prices:
            parent_avg_prices[p_asin] = sum(prices) / len(prices)

    return parent_avg_prices
