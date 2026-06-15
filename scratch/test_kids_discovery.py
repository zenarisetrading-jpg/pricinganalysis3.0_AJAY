import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import (
    fetch_account_products_with_categories,
    fetch_parent_asin_categories,
    fetch_competitors_by_category,
    filter_related_products,
    MARKETPLACE_MAP
)

p = 'B0DGLGPN1N'
cats = fetch_parent_asin_categories('oneshot_uae', p)
print(f"Categories for {p}: {cats}")

cat_ids = [c['category_id'] for c in cats]
print(f"Cat IDs: {cat_ids}")

for cid in cat_ids:
    pool = fetch_competitors_by_category(cid, 'UAE')
    print(f"Category {cid} pool size: {len(pool)}")
    
    # Check what is in the pool
    unique_asins = {item['asin'] for item in pool}
    print(f"Unique ASINs in pool: {len(unique_asins)}")
