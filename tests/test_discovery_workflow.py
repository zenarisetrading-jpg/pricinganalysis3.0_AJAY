import os
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before importing the service
sys.modules['psycopg2'] = MagicMock()
sys.modules['apify_client'] = MagicMock()
sys.modules['supabase'] = MagicMock()

# Import the service
from features.price_benchmarking.discovery_service import run_competitor_analysis_workflow

@patch('features.price_benchmarking.discovery_service.fetch_account_products_with_categories')
@patch('features.price_benchmarking.discovery_service.trigger_category_discovery')
@patch('features.price_benchmarking.apify_client.poll_for_results')
@patch('features.price_benchmarking.discovery_service.parse_apify_item')
@patch('features.price_benchmarking.snapshot_service.calculate_transient_upload_analysis')
@patch('features.price_benchmarking.discovery_service.get_supabase_client')
def test_workflow(mock_supabase, mock_analysis, mock_parse, mock_poll, mock_trigger, mock_fetch):
    # Mock data
    mock_fetch.return_value = [
        {
            "asin": "B0D39R47CC",
            "parent_asin": "B0PARENT123",
            "category_name": "Sports Supplements",
            "category_id": "12373047031",
            "marketplace_id": "A2VIGQ35RCS4UG",
        }
    ]
    mock_trigger.return_value = ("run_123", "ds_123")
    mock_poll.return_value = [
        {"asin": "COMP1", "price": 100.0, "title": "Comp 1", "brand": "Brand X"}
    ]
    mock_parse.return_value = {
        "asin": "COMP1",
        "floor_price": 100.0,
        "title": "Comp 1",
        "brand": "Brand X",
    }
    mock_analysis.return_value = {
        "status": "ok",
        "snapshots": [{
            "asin": "B0D39R47CC",
            "sku_id": "B0D39R47CC",
            "your_price": 120.0,
            "n_competitors": 1,
            "floor_price": 100.0,
            "ceiling_price": 100.0,
            "median_price": 100.0,
            "p25_price": 100.0,
            "p75_price": 100.0,
            "index_vs_median": 120.0,
            "zone": "premium",
            "strategy": "mid",
        }],
        "recommendations": [],
        "alerts": [],
    }
    
    # Mock Supabase listing
    mock_sb = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.gt.return_value = query
    query.limit.return_value = query
    query.insert.return_value = query
    query.upsert.return_value = query
    query.delete.return_value = query
    query.execute.side_effect = [
        MagicMock(data=[]),  # get_cached_analysis
        MagicMock(data=[]),  # freshness check
        MagicMock(data=[]),  # save_competitor_data insert
        MagicMock(data=[{"listing_price": 120.0, "strategy": "mid"}]),
        MagicMock(data=[]),
        MagicMock(data=[]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]
    mock_sb.table.return_value = query
    mock_supabase.return_value = mock_sb

    # Run workflow
    results = run_competitor_analysis_workflow("oneshot_uae")
    
    print("Workflow results:", results)
    
    # Assertions
    assert mock_fetch.call_count == 2
    mock_fetch.assert_any_call("oneshot_uae")
    mock_trigger.assert_not_called()
    mock_poll.assert_not_called()
    mock_analysis.assert_not_called()
    assert results["status"] == "processing"
    
    print("Workflow test passed (mocked)")

if __name__ == "__main__":
    test_workflow()
