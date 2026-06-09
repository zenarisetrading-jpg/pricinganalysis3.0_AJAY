import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import calculate_relevance_score

cat_diet = '12373019031'
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

matched = []
for c in pool_diet:
    title = c.get('title') or ''
    score = calculate_relevance_score('Electrolyte', title)
    if score >= 0.4:
        matched.append((c['asin'], title, score))

print(f"Matched competitors in Diet & Nutrition: {len(matched)}")
for asin, title, score in matched[:10]:
    print(f"  {asin} | score={score:.2f} | {title[:80]}")
