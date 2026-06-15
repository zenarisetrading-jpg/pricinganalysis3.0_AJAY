with open(r"d:\pricing_analysis\features\price_benchmarking\routes.py", "r", encoding="utf-8") as f:
    routes = f.read()

import re
matches = [m.start() for m in re.finditer(r'def _latest_snapshots_by_parent', routes)]

for m in matches:
    print(routes[m:m+1500])
    print("="*80)
