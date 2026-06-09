import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import calculate_relevance_score

pool = fetch_competitors_by_category('22202768031', 'UAE')
print(f"Total pool size: {len(pool)}")

matched = []
unmatched = []
for c in pool:
    title = c.get('title') or ''
    score = calculate_relevance_score('Electrolyte', title)
    if score >= 0.4:
        matched.append((c['asin'], score, title))
    else:
        unmatched.append((c['asin'], score, title))

print(f"Matched (score >= 0.4): {len(matched)}")
for asin, score, title in matched[:5]:
    print(f"  {asin} | score={score:.2f} | {title[:60]}")

print(f"\nUnmatched (score < 0.4): {len(unmatched)}")
for asin, score, title in unmatched[:5]:
    print(f"  {asin} | score={score:.2f} | {title[:60]}")
