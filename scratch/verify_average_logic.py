import sys
import os
sys.path.insert(0, '.')

from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_account_prices
from features.price_benchmarking.discovery_service import _build_parent_analysis_product

def test_average_pricing():
    sb = get_supabase_client()
    account_id = "oneshot_uae"
    
    # 1. Fetch products and actual prices
    products_data = fetch_account_products_with_categories(account_id)
    actual_prices = fetch_account_prices(account_id)
    
    # 2. Pick a target multi-variation ASIN: B0FNN5WKDG
    target_parent = "B0FNN5WKDG"
    parent_products = [p for p in products_data if p.get("parent_asin") == target_parent or p.get("asin") == target_parent]
    
    if not parent_products:
        print(f"Error: No products found for parent {target_parent}")
        return

    # Let's inspect variation prices manually first
    print(f"\n--- Checking individual variation prices for parent {target_parent} ---")
    prices_list = []
    for p in parent_products:
        asin = p["asin"]
        price = actual_prices.get(asin, 0.0)
        print(f"Variation ASIN: {asin} | Price: {price} AED")
        if price > 0:
            prices_list.append(price)
            
    manual_avg = sum(prices_list) / len(prices_list) if prices_list else 0.0
    print(f"Manual average of active child prices: {manual_avg:.2f} AED")

    # 3. Call our modified _build_parent_analysis_product function
    print(f"\n--- Running _build_parent_analysis_product for {target_parent} ---")
    result = _build_parent_analysis_product(
        sb=sb,
        account_id=account_id,
        parent_asin=target_parent,
        parent_products=parent_products,
        marketplace="UAE",
        category_ids=["12373047031"],
        actual_prices=actual_prices
    )
    
    calculated_price = result["price"]
    print(f"Calculated Parent Price from _build_parent_analysis_product: {calculated_price} AED")
    
    # Assert or print pass/fail
    if abs(calculated_price - manual_avg) < 0.01:
        print("\n✅ SUCCESS: Calculated price matches variation average perfectly!")
    else:
        print("\n❌ FAILURE: Mismatch in calculated parent price.")

if __name__ == "__main__":
    test_average_pricing()
