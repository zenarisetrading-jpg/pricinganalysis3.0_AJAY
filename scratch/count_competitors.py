import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

parents = ['B0DLX3GJNJ', 'B0DLX3Y8JN', 'B0DLX4FKPT', 'B0DLXPQZCJ', 'B0FM43BSB2', 'B0FM45GBTY', 'B0FNN5WKDG']

print("ROW COUNTS IN competitor_products AFTER RECALC:")
for p in parents:
    res = sb.table('competitor_products').select('count', count='exact').eq('parent_asin', p).execute()
    print(f"Parent: {p} | Row count: {res.count}")
