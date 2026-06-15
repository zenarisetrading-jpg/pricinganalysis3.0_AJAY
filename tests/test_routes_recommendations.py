from features.price_benchmarking.routes import (
    _latest_recommendations_by_parent,
    _latest_snapshots_by_parent,
    get_recommendations,
    get_overview,
)
from unittest.mock import MagicMock, patch
import pytest

# ... (rest of unchanged functions inside file) ...
def test_latest_snapshots_by_parent_prefers_parent_row_on_same_date() -> None:
    rows = [
        {
            "asin": "CHILD1",
            "snapshot_date": "2026-05-18",
            "index_vs_median": 120,
        },
        {
            "asin": "PARENT1",
            "parent_asin": "PARENT1",
            "snapshot_date": "2026-05-18",
            "index_vs_median": 95,
        },
    ]

    latest = _latest_snapshots_by_parent(rows, {"CHILD1": "PARENT1"})

    assert len(latest) == 1
    assert latest[0]["asin"] == "PARENT1"


@pytest.mark.anyio
async def test_get_recommendations_attaches_title_and_ref_name() -> None:
    mock_supabase = MagicMock()
    
    # Setup chain for recommendations table query
    mock_recs_resp = MagicMock()
    mock_recs_resp.execute.return_value.data = [
        {
            "asin": "CHILD1",
            "parent_asin": "PARENT1",
            "current_price": 20.0,
            "recommended_price": 18.0,
            "action": "decrease",
            "reasoning": "some reasoning",
            "status": "pending",
            "snapshot_date": "2026-05-18",
            "created_at": "2026-05-18T10:00:00",
        }
    ]
    
    # Setup chain for pb_client_listings query
    mock_listings_resp = MagicMock()
    mock_listings_resp.execute.return_value.data = [
        {"asin": "CHILD1", "reference_name": "Test Product"}
    ]
    
    # Mock supabase table method to return appropriate mock based on table name
    def mock_table(table_name):
        if table_name == "pb_recommendations":
            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value = mock_recs_resp
            return mock_query
        elif table_name == "pb_client_listings":
            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value = mock_listings_resp
            return mock_query
        return MagicMock()
        
    mock_supabase.table.side_effect = mock_table

    with patch("features.price_benchmarking.saddl_db.fetch_account_prices") as mock_prices, \
         patch("features.price_benchmarking.saddl_db.fetch_account_products_with_categories") as mock_products, \
         patch("features.price_benchmarking.routes._load_account_parent_map") as mock_parent_map, \
         patch("features.price_benchmarking.routes.ensure_client_exists") as mock_ensure:
         
        mock_parent_map.return_value = ({"CHILD1": "PARENT1"}, {"PARENT1"})
        mock_prices.return_value = {"CHILD1": 20.0}
        mock_products.return_value = [
            {"asin": "CHILD1", "parent_asin": "PARENT1", "title": "Real Product Title", "category_name": "Cat", "category_id": 1, "marketplace_id": "1"}
        ]
        
        result = await get_recommendations(client_id="test_client", supabase=mock_supabase)
        
        assert "recommendations" in result
        assert len(result["recommendations"]) == 1
        rec = result["recommendations"][0]
        assert rec["title"] == "Real Product Title"
        assert rec["reference_name"] == "Test Product"


@pytest.mark.anyio
async def test_get_overview_attaches_title_and_ref_name() -> None:
    mock_supabase = MagicMock()
    
    # Setup chain for snapshots query
    mock_snapshots_resp = MagicMock()
    mock_snapshots_resp.execute.return_value.data = [
        {
            "asin": "CHILD1",
            "sku_id": "SKU1",
            "snapshot_date": "2026-05-18",
            "index_vs_median": 105,
            "zone": "value",
            "your_price": 20.0,
            "n_competitors": 5,
        }
    ]
    
    # Setup chain for pb_client_listings query
    mock_listings_resp = MagicMock()
    mock_listings_resp.execute.return_value.data = [
        {"asin": "CHILD1", "reference_name": "Test Product"}
    ]
    
    # Mock supabase table method
    def mock_table(table_name):
        if table_name == "pb_client_snapshots_daily":
            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value.order.return_value = mock_snapshots_resp
            return mock_query
        elif table_name == "pb_client_listings":
            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value = mock_listings_resp
            return mock_query
        return MagicMock()
        
    mock_supabase.table.side_effect = mock_table

    with patch("features.price_benchmarking.saddl_db.fetch_account_products_with_categories") as mock_products, \
         patch("features.price_benchmarking.routes.ensure_client_exists") as mock_ensure:
         
        mock_products.return_value = [
            {"asin": "CHILD1", "parent_asin": "PARENT1", "title": "Real Product Title", "category_name": "Cat", "category_id": 1, "marketplace_id": "1"}
        ]
        
        result = await get_overview(client_id="test_client", supabase=mock_supabase)
        
        assert "rows" in result
        assert len(result["rows"]) == 1
        row = result["rows"][0]
        assert row["title"] == "Real Product Title"
        assert row["reference_name"] == "Test Product"
