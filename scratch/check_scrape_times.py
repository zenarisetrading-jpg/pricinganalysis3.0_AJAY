import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

cat1 = '12373019031' # Diet & Nutrition
cat2 = '12373047031' # Sports Supplements

res1 = sb.table('competitor_products').select('scraped_at').eq('category_id', cat1).order('scraped_at', desc=True).limit(1).execute()
res2 = sb.table('competitor_products').select('scraped_at').eq('category_id', cat2).order('scraped_at', desc=True).limit(1).execute()

print(f"Last scrape for {cat1} (Diet & Nutrition): {res1.data[0]['scraped_at'] if res1.data else 'NEVER'}")
print(f"Last scrape for {cat2} (Sports Supplements): {res2.data[0]['scraped_at'] if res2.data else 'NEVER'}")
