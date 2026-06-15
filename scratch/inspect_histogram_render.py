import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r'function renderPricingHistogram', html)]

for m in matches:
    print(html[m:m+4000])
    print("="*80)
