from features.price_benchmarking.benchmarking import calculate_benchmarks
from features.price_benchmarking.discovery_service import fetch_competitor_data
import json

asin = "B0CZLK598D"
marketplace = "UAE"
competitors = fetch_competitor_data(asin, marketplace)
snap = {"asin": asin, "price": 99.0} # Fake snapshot
results = calculate_benchmarks(asin, marketplace, competitors, snap)
print(json.dumps(results.get("alerts", []), indent=2))
