with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r'overview-product-selector', html)]
print("Occurrences of selector in JS:")
for m in matches:
    print(html[max(0, m-150):min(len(html), m+300)])
    print("="*80)
