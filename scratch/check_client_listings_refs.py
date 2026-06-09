import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

res = sb.table('pb_client_listings').select('asin', 'reference_name', 'listing_price', 'price').eq('client_id', 'oneshot_uae').execute()
print("CLIENT LISTINGS IN DB:")
for r in res.data:
    print(f"ASIN: {r['asin']} | Ref: '{r.get('reference_name')}' | List Price: {r.get('listing_price')} | Price: {r.get('price')}")
