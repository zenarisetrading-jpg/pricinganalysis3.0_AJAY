import sys
import os

# Add the workspace root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from features.price_benchmarking.snapshot_service import _resolve_majority_categories

def run_tests():
    print("Running Category Resolution Unit Tests...")

    # Case 1: Simple Majority
    products = [
        {"parent_asin": "PARENT1", "asin": "CHILD1", "category_name": "Sports Bottles", "category_id": "1", "category_ids": ["1"]},
        {"parent_asin": "PARENT1", "asin": "CHILD2", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT1", "asin": "CHILD3", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
    ]
    resolved = _resolve_majority_categories(products)
    
    assert resolved[0]["category_name"] == "Water Bottles", f"Expected Water Bottles, got {resolved[0]['category_name']}"
    assert resolved[1]["category_name"] == "Water Bottles"
    assert resolved[2]["category_name"] == "Water Bottles"
    assert resolved[0]["category_id"] == "2"
    assert resolved[0]["category_ids"] == ["2"]
    print("[OK] Case 1: Simple Majority Passed!")

    # Case 2: Tie breaking (Alphabetical sort)
    # "Sports Bottles" vs "Water Bottles" (1 vs 1) -> "Sports Bottles" wins because S < W
    products_tie = [
        {"parent_asin": "PARENT2", "asin": "CHILD1", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT2", "asin": "CHILD2", "category_name": "Sports Bottles", "category_id": "1", "category_ids": ["1"]},
    ]
    resolved_tie = _resolve_majority_categories(products_tie)
    assert resolved_tie[0]["category_name"] == "Sports Bottles", f"Expected Sports Bottles (S < W), got {resolved_tie[0]['category_name']}"
    assert resolved_tie[1]["category_name"] == "Sports Bottles"
    assert resolved_tie[0]["category_id"] == "1"
    print("[OK] Case 2: Tie-breaking Alphabetical Fallback Passed!")

    # Case 3: Mixed parent_asin presence and None values
    products_mixed = [
        {"parent_asin": None, "asin": "CHILD1", "category_name": "Isolated Cat", "category_id": "99", "category_ids": ["99"]},
        {"parent_asin": "PARENT3", "asin": "CHILD2", "category_name": None, "category_id": None, "category_ids": []},
        {"parent_asin": "PARENT3", "asin": "CHILD3", "category_name": "Home & Kitchen", "category_id": "5", "category_ids": ["5"]},
    ]
    resolved_mixed = _resolve_majority_categories(products_mixed)
    # The one with None parent_asin should remain untouched
    assert resolved_mixed[0]["category_name"] == "Isolated Cat"
    # PARENT3 should resolve to "Home & Kitchen" because it's the only category info present
    assert resolved_mixed[1]["category_name"] == "Home & Kitchen"
    assert resolved_mixed[2]["category_name"] == "Home & Kitchen"
    assert resolved_mixed[1]["category_id"] == "5"
    print("[OK] Case 3: Mixed parent_asins and None values Passed!")

    # Case 4: Category ID fallback (No names present)
    products_ids = [
        {"parent_asin": "PARENT4", "asin": "CHILD1", "category_name": None, "category_id": "300", "category_ids": ["300"]},
        {"parent_asin": "PARENT4", "asin": "CHILD2", "category_name": None, "category_id": "200", "category_ids": ["200"]},
        {"parent_asin": "PARENT4", "asin": "CHILD3", "category_name": None, "category_id": "200", "category_ids": ["200"]},
    ]
    resolved_ids = _resolve_majority_categories(products_ids)
    assert resolved_ids[0]["category_id"] == "200", f"Expected category_id 200, got {resolved_ids[0]['category_id']}"
    assert resolved_ids[1]["category_id"] == "200"
    assert resolved_ids[2]["category_id"] == "200"
    print("[OK] Case 4: Category ID fallback Passed!")

    # Case 5: Case insensitivity normalization
    products_case = [
        {"parent_asin": "PARENT5", "asin": "CHILD1", "category_name": "water bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT5", "asin": "CHILD2", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT5", "asin": "CHILD3", "category_name": "Sports Bottles", "category_id": "1", "category_ids": ["1"]},
    ]
    resolved_case = _resolve_majority_categories(products_case)
    # "water bottles" + "Water Bottles" = 2 count, "Sports Bottles" = 1 count.
    # So "water bottles" (or "Water Bottles") should win.
    # The winner casing should match the first occurrence.
    assert resolved_case[0]["category_name"] in ["water bottles", "Water Bottles"], f"Expected water bottles variation, got {resolved_case[0]['category_name']}"
    assert resolved_case[1]["category_name"] in ["water bottles", "Water Bottles"]
    assert resolved_case[2]["category_name"] in ["water bottles", "Water Bottles"]
    assert resolved_case[0]["category_id"] == "2"
    print("[OK] Case 5: Case insensitivity normalization Passed!")

    # Case 6: UI Category Selector Filtering (Exact duplicate resolution in UI categories)
    # Mock categories list from SADDL query
    categories_raw = [
        {
            "category_name": "Sports Bottles",
            "products": [
                {"asin": "PARENT6", "rank": 10, "title": "Bottle A"}
            ]
        },
        {
            "category_name": "Water Bottles",
            "products": [
                {"asin": "PARENT6", "rank": 5, "title": "Bottle A"}
            ]
        }
    ]
    # PARENT6 has 2 child variations in saddl:
    # Child 1: category_name = "Water Bottles" (Dominant because we have 2 children in Water Bottles, 1 in Sports Bottles)
    # Child 2: category_name = "Water Bottles"
    # Child 3: category_name = "Sports Bottles"
    saddl_products_mock = [
        {"parent_asin": "PARENT6", "asin": "C1", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT6", "asin": "C2", "category_name": "Water Bottles", "category_id": "2", "category_ids": ["2"]},
        {"parent_asin": "PARENT6", "asin": "C3", "category_name": "Sports Bottles", "category_id": "1", "category_ids": ["1"]},
    ]
    # Run resolution
    saddl_resolved = _resolve_majority_categories(saddl_products_mock)
    
    parent_to_resolved_category = {}
    for p in saddl_resolved:
        parent = p.get("parent_asin")
        cat_name = p.get("category_name")
        if parent and cat_name:
            parent_to_resolved_category[parent.strip()] = cat_name.strip()

    # Apply filtering
    filtered_categories = []
    for c in categories_raw:
        c_name_norm = c["category_name"].strip().lower()
        filtered_products = []
        for p in c.get("products", []):
            parent = p.get("asin")
            if parent:
                resolved_cat = parent_to_resolved_category.get(parent.strip())
                if resolved_cat and resolved_cat.strip().lower() == c_name_norm:
                    filtered_products.append(p)
                elif not resolved_cat:
                    filtered_products.append(p)
            else:
                filtered_products.append(p)
        if filtered_products:
            c["products"] = filtered_products
            filtered_categories.append(c)

    # PARENT6's dominant category is "Water Bottles". So it should be removed from "Sports Bottles" and kept only in "Water Bottles".
    # As a result, "Sports Bottles" category should have 0 products and be filtered out.
    assert len(filtered_categories) == 1, f"Expected 1 category, got {len(filtered_categories)}"
    assert filtered_categories[0]["category_name"] == "Water Bottles", f"Expected Water Bottles, got {filtered_categories[0]['category_name']}"
    assert filtered_categories[0]["products"][0]["asin"] == "PARENT6"
    print("[OK] Case 6: UI Category Selector Filtering Passed!")

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
