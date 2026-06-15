from db import get_supabase_client
sb = get_supabase_client()
data = sb.table('competitor_products').select('category_id').execute().data
unique_cats = set(r['category_id'] for r in data)
print(f"Total rows: {len(data)}")
print(f"Unique Category IDs: {unique_cats}")
