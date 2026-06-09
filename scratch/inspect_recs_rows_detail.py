import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
match = re.search(r'function renderRecommendations\(recs\).*?<\/tbody>', html, re.DOTALL)
if match:
    print(match.group(0))
else:
    # let's just search for processedRecs
    matches = [m.start() for m in re.finditer(r'processedRecs', html)]
    for m in matches:
        print(html[m:m+1200])
        print("="*80)
