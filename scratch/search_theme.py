with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
matches = [line.strip() for line in html.split("\n") if "theme" in line.lower() or "light" in line.lower()]
print(f"Found {len(matches)} occurrences:")
for m in matches[:20]:
    print(m)
