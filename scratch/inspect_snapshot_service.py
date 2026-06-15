with open(r"d:\pricing_analysis\features\price_benchmarking\snapshot_service.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r'your_price', content)]
print("Found your_price at indices:", matches)
for m in matches[:5]:
    print(content[max(0, m-200):min(len(content), m+300)])
    print("="*80)
