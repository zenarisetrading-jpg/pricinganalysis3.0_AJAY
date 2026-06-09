import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
match = re.search(r'<nav class="nav-list">.*?</nav>', html, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Could not find nav-list")
