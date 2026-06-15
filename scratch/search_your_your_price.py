with open(r"d:\pricing_analysis\features\price_benchmarking\routes.py", "r", encoding="utf-8") as f:
    routes = f.read()

import re
matches = [m.start() for m in re.finditer(r'your_price', routes)]
print(f"Found your_price in routes.py at indices: {matches}")
for m in matches:
    print(routes[max(0, m-200):min(len(routes), m+300)])
    print("="*80)
