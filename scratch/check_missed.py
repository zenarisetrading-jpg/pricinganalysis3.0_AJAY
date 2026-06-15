import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import calculate_relevance_score

cat_diet = '12373019031'
cat_sports = '12373047031'

pool_diet = fetch_competitors_by_category(cat_diet, 'UAE')
pool_sports = fetch_competitors_by_category(cat_sports, 'UAE')

all_pool = pool_diet + pool_sports
seen = set()
unique_all = []
for c in all_pool:
    if c['asin'] not in seen:
        unique_all.append(c)
        seen.add(c['asin'])

print(f"Total unique competitor products: {len(unique_all)}")
missed = []
for c in unique_all:
    title = c.get('title') or ''
    if 'electrolyte' in title.lower():
        score = calculate_relevance_score('Electrolyte', title)
        if score < 0.4:
            missed.append((c['asin'], title, score))

print(f"Missed products containing 'electrolyte' in title (score < 0.4): {len(missed)}")
for asin, title, score in missed:
    print(f"  ASIN: {asin} | Score: {score:.2f} | Title: {title}")
