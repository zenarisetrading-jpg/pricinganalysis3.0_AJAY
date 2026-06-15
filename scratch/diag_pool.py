import sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories, fetch_parent_asin_categories

sb = get_supabase_client()

# 1. What category does B0FNN5WKDG belong to?
cats = fetch_parent_asin_categories('oneshot_uae', 'B0FNN5WKDG')
print("Categories for B0FNN5WKDG:", cats)

# 2. How many competitors per category_id?
for cat in cats:
    cat_id = cat['category_id']
    res = sb.table('competitor_products').select('competitor_asin', count='exact').eq('category_id', cat_id).eq('marketplace', 'UAE').execute()
    print(f"  category_id={cat_id} ({cat['category_name']}): {res.count} competitors by category_id")

# 3. How many by parent_asin?
res2 = sb.table('competitor_products').select('competitor_asin', count='exact').eq('parent_asin', 'B0FNN5WKDG').eq('marketplace', 'UAE').execute()
print(f"  By parent_asin=B0FNN5WKDG: {res2.count} competitors")

# 4. How many have NULL category_id?
res3 = sb.table('competitor_products').select('competitor_asin', count='exact').eq('parent_asin', 'B0FNN5WKDG').is_('category_id', 'null').execute()
print(f"  Of those, NULL category_id: {res3.count}")
