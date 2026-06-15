import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

res1 = sb.table('competitor_products').select('competitor_asin, competitor_title, category_id').eq('parent_asin', 'B0DLX3GJNJ').execute()
res2 = sb.table('competitor_products').select('competitor_asin, competitor_title, category_id').eq('parent_asin', 'B0FNN5WKDG').execute()

print("COMPETITORS SAVED FOR B0DLX3GJNJ:")
for r in sorted(res1.data, key=lambda x: x['competitor_asin']):
    title = r['competitor_title'].encode('ascii', 'ignore').decode('ascii')
    print(f"  {r['competitor_asin']} | {r['category_id']} | {title[:60]}")

print("\nCOMPETITORS SAVED FOR B0FNN5WKDG:")
for r in sorted(res2.data, key=lambda x: x['competitor_asin']):
    title = r['competitor_title'].encode('ascii', 'ignore').decode('ascii')
    print(f"  {r['competitor_asin']} | {r['category_id']} | {title[:60]}")
