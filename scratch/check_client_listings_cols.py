import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

res = sb.table('pb_client_listings').select('*').limit(1).execute()
if res.data:
    print("Columns in pb_client_listings:", list(res.data[0].keys()))
    print("Example listing:", res.data[0])
else:
    print("pb_client_listings is empty!")
