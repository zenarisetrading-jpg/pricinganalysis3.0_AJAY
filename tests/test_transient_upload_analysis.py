from features.price_benchmarking.routes import calculate_transient_upload_analysis


def test_transient_upload_analysis_uses_only_uploaded_files() -> None:
    products = [
        {
            "asin": "OWN1",
            "sku": "SKU-1",
            "price": 15.0,
            "marketplace": "UAE",
            "category_name": "Storage Boxes",
        }
    ]
    competitors = [
        {"asin": "COMP1", "price": 10.0, "marketplace": "UAE", "category_name": "Storage Boxes"},
        {"asin": "COMP2", "price": 12.0, "marketplace": "UAE", "category_name": "Storage Boxes"},
        {"asin": "COMP3", "price": 14.0, "marketplace": "UAE", "category_name": "Storage Boxes"},
        {"asin": "COMP4", "price": 18.0, "marketplace": "UAE", "category_name": "Storage Boxes"},
        {"asin": "OTHER1", "price": 1.0, "marketplace": "UAE", "category_name": "Other"},
    ]

    result = calculate_transient_upload_analysis(
        client_id="test-client",
        products=products,
        competitor_records=competitors,
    )

    assert result["source"] == "uploaded_files_only"
    assert result["n_asins"] == 1
    assert result["snapshots"][0]["asin"] == "OWN1"
    assert result["snapshots"][0]["n_competitors"] == 4
    assert result["snapshots"][0]["floor_price"] == 10.0
    assert result["snapshots"][0]["median_price"] == 13.0
    assert result["recommendations"][0]["asin"] == "OWN1"


def test_transient_upload_analysis_returns_local_tab_payloads() -> None:
    products = [
        {
            "asin": "OWN1",
            "sku": "SKU-1",
            "price": 15.0,
            "marketplace": "UAE",
            "category_name": "Storage Boxes",
            "bsr_rank": 100,
            "units_ordered": 4,
            "sessions": 100,
            "acos": 22.5,
        }
    ]
    competitors = [
        {"asin": "COMP1", "price": 10.0, "marketplace": "UAE", "category_name": "Storage Boxes", "sales_rank": 200},
        {"asin": "COMP2", "price": 12.0, "marketplace": "UAE", "category_name": "Storage Boxes", "sales_rank": 300},
        {"asin": "COMP3", "price": 14.0, "marketplace": "UAE", "category_name": "Storage Boxes", "sales_rank": 400},
    ]

    result = calculate_transient_upload_analysis(
        client_id="test-client",
        products=products,
        competitor_records=competitors,
    )

    assert result["performance"][0]["asin"] == "OWN1"
    assert result["performance"][0]["cvr"] == 4.0
    assert result["categories"] == [
        {
            "category_name": "Storage Boxes",
            "asin_count": 4,
            "asins": ["COMP1", "COMP2", "COMP3", "OWN1"],
            "avg_rank": 250.0,
        }
    ]


def test_transient_upload_analysis_uses_parent_category_set() -> None:
    products = [
        {
            "asin": "OWN1",
            "sku": "SKU-1",
            "price": 15.0,
            "marketplace": "UAE",
            "category_id": "CAT-A",
            "category_ids": ["CAT-A", "CAT-B"],
        }
    ]
    competitors = [
        {"asin": "COMP1", "price": 10.0, "marketplace": "UAE", "category_id": "CAT-A"},
        {"asin": "COMP2", "price": 12.0, "marketplace": "UAE", "category_id": "CAT-B"},
        {"asin": "COMP3", "price": 14.0, "marketplace": "UAE", "category_id": "CAT-B"},
        {"asin": "COMP4", "price": 18.0, "marketplace": "UAE", "category_id": "CAT-C"},
    ]

    result = calculate_transient_upload_analysis(
        client_id="test-client",
        products=products,
        competitor_records=competitors,
    )

    assert result["n_asins"] == 1
    assert result["snapshots"][0]["n_competitors"] == 3
    assert result["snapshots"][0]["floor_price"] == 10.0
    assert result["snapshots"][0]["ceiling_price"] == 14.0


def test_transient_upload_analysis_populates_parent_asin() -> None:
    products = [
        {
            "asin": "OWN1",
            "parent_asin": "PARENT1",
            "sku": "SKU-1",
            "price": 15.0,
            "marketplace": "UAE",
            "category_name": "Storage Boxes",
        }
    ]
    competitors = [
        {"asin": "COMP1", "price": 10.0, "marketplace": "UAE", "category_name": "Storage Boxes"},
    ]

    result = calculate_transient_upload_analysis(
        client_id="test-client",
        products=products,
        competitor_records=competitors,
    )

    assert result["n_asins"] == 1
    assert result["snapshots"][0]["parent_asin"] == "PARENT1"
    assert result["recommendations"][0]["parent_asin"] == "PARENT1"
    assert len(result["alerts"]) > 0
    assert result["alerts"][0]["parent_asin"] == "PARENT1"
