with open(r"d:\pricing_analysis\dashboard\price_benchmarking.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
match = re.search(r'// Overview Product Selector Change Event.*?\n\s*\n', html, re.DOTALL)
if match:
    print(match.group(0))
else:
    # try showing surrounding lines of ovProdSelector
    idx = html.find("Overview Product Selector Change Event")
    if idx != -1:
        print(html[idx:idx+1500])
    else:
        print("Not found")
