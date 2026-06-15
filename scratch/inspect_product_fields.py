import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
# find all occurrences of your_price or median_price in the html
matches = [m.start() for m in re.finditer(r'your_price|median_price', html)]

seen = set()
for m in matches:
    # get line
    start = html.rfind("\n", 0, m)
    end = html.find("\n", m)
    line = html[start+1:end].strip()
    if line not in seen:
        seen.add(line)
        print(line)
