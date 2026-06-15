import sys
sys.path.insert(0, '.')
from db import get_supabase_client

sb = get_supabase_client()
parent = 'B0FWKSMV4J'

# Check pb_recommendations metadata
print("Checking pb_recommendations metadata...")
res = sb.table('pb_recommendations').select('asin, client_id, metadata').eq('asin', parent).execute()
if res.data:
    row = res.data[0]
    print(f"Parent {parent} belongs to client_id: {row.get('client_id')}")
    meta = row.get('metadata') or {}
    competitors = meta.get('competitors') or []
    print(f"Found {len(competitors)} competitors in recommendation metadata.")
    if competitors:
        print("First 5 competitors:")
        for c in competitors[:5]:
            title = c.get('title') or ''
            title_clean = title.encode('ascii', 'ignore').decode()[:40]
            print(f"  ASIN: {c.get('asin')}, Brand: {c.get('brand')}, Title: {title_clean}, Price: {c.get('price')}")
else:
    print("No pb_recommendations found for B0FWKSMV4J")

# Check competitor_products
print("\nChecking competitor_products...")
res2 = sb.table('competitor_products').select('competitor_asin, competitor_title, brand, competitor_price').eq('parent_asin', parent).execute()
if res2.data:
    print(f"Found {len(res2.data)} products in competitor_products.")
    print("First 5:")
    for r in res2.data[:5]:
        title = r.get('competitor_title') or ''
        title_clean = title.encode('ascii', 'ignore').decode()[:40]
        print(f"  ASIN: {r.get('competitor_asin')}, Brand: {r.get('brand')}, Title: {title_clean}, Price: {r.get('competitor_price')}")
else:
    print("No competitor_products found for B0FWKSMV4J")
