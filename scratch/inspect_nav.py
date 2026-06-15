import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for sidebar nav or class="nav" or role="tablist"
import re
matches = [m.start() for m in re.finditer(r'nav-list|nav-link|tab-', html)]

for m in sorted(list(set(matches)))[:10]:
    print(html[max(0, m-200):min(len(html), m+300)])
    print("="*80)
