with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'data-asin="${r.parent_asin' in line or 'action-chip action-' in line:
        print(f"Line {i+1}: {line.strip()}")
