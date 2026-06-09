with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- CARD BODY LOCATIONS ---")
for i, line in enumerate(lines):
    if "overview-product-selector" in line:
        print(f"Selector at line {i+1}: {line.strip()}")
    if "overview-chart-loading" in line:
        print(f"Loading at line {i+1}: {line.strip()}")
    if "function renderPricingHistogram" in line:
        print(f"renderPricingHistogram at line {i+1}: {line.strip()}")
