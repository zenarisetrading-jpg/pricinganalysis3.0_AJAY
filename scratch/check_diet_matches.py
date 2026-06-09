import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import calculate_relevance_score

cat_diet = '12373019031'
pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')

print(f"Total competitors in Diet & Nutrition: {len(pool_diet)}")
matching_diet = []
for c in pool_diet:
    title = c.get('title') or ''
    score = calculate_relevance_score('Electrolyte', title)
    if 'electrolyte' in title.lower() or score >= 0.4:
        matching_diet.append((c['asin'], title, score))

print(f"Number of matching competitors in Diet & Nutrition: {len(matching_diet)}")
for asin, title, score in matching_diet[:10]:
    print(f"ASIN: {asin} | Score: {score:.2f} | Title: {title}")
