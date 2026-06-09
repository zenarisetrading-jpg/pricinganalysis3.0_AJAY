import sys
import os

# Add parent directory to path to import features correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from features.price_benchmarking.relevance_filter import calculate_relevance_score, is_related, filter_related_products

def test_exclude_keywords():
    print("Running Exclude Competitor Keywords Relevance Tests...\n")
    
    # 1. Test Only Exclude Keywords (no reference name)
    # The competitor titles containing 'charger' or 'accessory' should be excluded.
    target_1 = {
        "asin": "B012345678",
        "title": "Phone Holder for Car",
        "exclude_keywords": "charger, accessory"
    }
    
    competitors_1 = [
        {"asin": "B000000001", "title": "Car Phone Holder Dashboard Mount", "expected": True},
        {"asin": "B000000002", "title": "Fast Wireless Charger Car Mount", "expected": False},
        {"asin": "B000000003", "title": "Car Vent Mount Phone Accessory Pack", "expected": False},
        {"asin": "B000000004", "title": "Magnetic Car Cradle Stand", "expected": True},
    ]
    
    print("--- Test 1: Only Exclude Keywords ---")
    for comp in competitors_1:
        related = is_related(target_1, comp)
        passed = (related == comp["expected"])
        print(f"[{'PASS' if passed else 'FAIL'}] Title: '{comp['title']}' -> Related: {related} (Expected: {comp['expected']})")
        assert passed, f"Failed for {comp['title']}"

    # 2. Test Both Include (Reference Name) and Exclude Keywords
    target_2 = {
        "asin": "B012345678",
        "reference_name": "Electrolyte Hydration Powder",
        "exclude_keywords": "gummies, tablet"
    }
    
    competitors_2 = [
        {"asin": "B000000001", "title": "Liquid I.V. Hydration Multiplier - Electrolyte Powder", "expected": True},
        {"asin": "B000000002", "title": "Electrolyte Hydration Gummies Chewables", "expected": False},
        {"asin": "B000000003", "title": "Hydration Electrolyte Tablets - Effervescent", "expected": False},
        {"asin": "B000000004", "title": "Optimum Nutrition Gold Standard Whey Protein Powder", "expected": False}, # doesn't match reference name
    ]
    
    print("\n--- Test 2: Both Include & Exclude Keywords ---")
    for comp in competitors_2:
        related = is_related(target_2, comp)
        passed = (related == comp["expected"])
        print(f"[{'PASS' if passed else 'FAIL'}] Title: '{comp['title']}' -> Related: {related} (Expected: {comp['expected']})")
        assert passed, f"Failed for {comp['title']}"

    # 3. Test filter_related_products with exclude keywords
    candidates = [
        {"asin": "B000000001", "title": "Super Electrolyte Hydration Powder Packets"},
        {"asin": "B000000002", "title": "Electrolyte Tablets Orange Flavor"},
        {"asin": "B000000003", "title": "Electrolyte Gummies For Sport"},
    ]
    
    print("\n--- Test 3: filter_related_products with exclude_keywords ---")
    filtered = filter_related_products(target_2, candidates)
    filtered_asins = [p["asin"] for p in filtered]
    
    # B000000001 is a match for "Electrolyte Hydration Powder" and doesn't contain exclude keywords
    # B000000002 has "tablets" (exclude "tablet") -> excluded
    # B000000003 has "gummies" (exclude "gummies") -> excluded
    expected_asins = ["B000000001"]
    passed_filter = (filtered_asins == expected_asins)
    print(f"[{'PASS' if passed_filter else 'FAIL'}] Filtered ASINs: {filtered_asins} (Expected: {expected_asins})")
    assert passed_filter, f"Failed filter_related_products: got {filtered_asins}"

    print("\nAll exclude keywords relevance tests passed successfully!")

if __name__ == "__main__":
    test_exclude_keywords()
