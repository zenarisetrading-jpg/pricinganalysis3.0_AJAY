with open(r"d:\pricing_analysis\features\price_benchmarking\routes.py", "r", encoding="utf-8") as f:
    routes = f.read()

import re
matches = [m.start() for m in re.finditer(r'@router\.get\("(/overview|/recommendations)"', routes)]

for m in matches:
    end = routes.find("def ", m)
    func_end = routes.find("\n\n", end + 10)
    # print about 200 lines from m
    print(routes[m:m+1500])
    print("="*80)
