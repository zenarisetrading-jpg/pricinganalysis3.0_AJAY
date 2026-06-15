from features.price_benchmarking.benchmarking import BenchmarkResult, PriceZone
from features.price_benchmarking.recommendations import RepricingStrategy, recommend


def make_result(your_price: float = 20.0) -> BenchmarkResult:
    return BenchmarkResult(
        sku_id="SKU-1",
        asin="ASIN1",
        marketplace="UAE",
        your_price=your_price,
        currency="AED",
        n_competitors=8,
        floor=10.0,
        ceiling=30.0,
        median=20.0,
        p25=15.0,
        p75=25.0,
        mean=20.0,
        percentile_rank=50.0,
        zone=PriceZone.VALUE,
        gap_to_floor=10.0,
        gap_to_median=0.0,
        gap_to_ceiling=-10.0,
        index_vs_median=100.0,
        competitors=[],
    )


def make_empty_result() -> BenchmarkResult:
    result = make_result()
    result.n_competitors = 0
    result.floor = 0.0
    result.ceiling = 0.0
    result.median = 0.0
    result.p25 = 0.0
    result.p75 = 0.0
    return result


def test_recommend_mid_strategy_targets_median() -> None:
    result = make_result(your_price=20.0)
    result.median = 18.0

    recommendation = recommend(result, strategy=RepricingStrategy.MID)

    assert recommendation.recommended_price == 18.0
    assert recommendation.action == "decrease"


def test_recommendation_acos_guard_suppresses_price_cut() -> None:
    result = make_result(your_price=28.0)

    recommendation = recommend(
        result,
        strategy=RepricingStrategy.MID,
        avg_acos=40.0,
    )

    assert recommendation.recommended_price == 20.0
    assert recommendation.action == "hold"
    assert "ACoS is 40.0%" in recommendation.reasoning


def test_zero_competitor_reasoning_does_not_mention_keyword_without_reference() -> None:
    recommendation = recommend(make_empty_result(), strategy=RepricingStrategy.MID)

    assert "category pool" in recommendation.reasoning
    assert "keyword" not in recommendation.reasoning


def test_zero_competitor_reasoning_mentions_keyword_with_reference() -> None:
    recommendation = recommend(
        make_empty_result(),
        strategy=RepricingStrategy.MID,
        reference_name="hydration powder",
    )

    assert "matched your keyword" in recommendation.reasoning
