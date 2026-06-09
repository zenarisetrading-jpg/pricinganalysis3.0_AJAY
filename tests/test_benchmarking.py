from features.price_benchmarking.benchmarking import (
    CompetitorPrice,
    PriceZone,
    compute_benchmark,
)


def test_compute_benchmark_classifies_mid_market_position() -> None:
    competitors = [
        CompetitorPrice(asin="A1", title="Comp 1", price=10.0, is_fba=True),
        CompetitorPrice(asin="A2", title="Comp 2", price=12.0, is_fba=True),
        CompetitorPrice(asin="A3", title="Comp 3", price=14.0, is_fba=False),
        CompetitorPrice(asin="A4", title="Comp 4", price=18.0, is_fba=True),
    ]

    result = compute_benchmark(
        sku_id="SKU-1",
        asin="SELF1",
        your_price=15.0,
        competitors=competitors,
        marketplace="UAE",
    )

    assert result is not None
    assert result.floor == 10.0
    assert result.ceiling == 18.0
    assert result.median == 13.0
    assert result.zone == PriceZone.MID_MARKET
    assert result.index_vs_median == round((15.0 / 13.0) * 100, 1)


def test_compute_benchmark_returns_none_with_too_few_competitors() -> None:
    competitors = [
        CompetitorPrice(asin="A1", title="Comp 1", price=10.0, is_fba=True),
        CompetitorPrice(asin="A2", title="Comp 2", price=12.0, is_fba=True),
    ]

    result = compute_benchmark(
        sku_id="SKU-1",
        asin="SELF1",
        your_price=11.0,
        competitors=competitors,
        marketplace="UAE",
    )

    assert result is not None
    assert result.n_competitors == 2
    assert result.floor == 10.0
    assert result.ceiling == 12.0
