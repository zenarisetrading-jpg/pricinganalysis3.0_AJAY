
import sys
import os
sys.path.append('.')
from db import get_supabase_client

def verify():
    sb = get_supabase_client()
    res = sb.table('pb_client_listings').select('asin, category_id').eq('client_id', 'oneshot_uae').execute()
    print("--- PB_CLIENT_LISTINGS (oneshot_uae) ---")
    for r in res.data:
        print(f"ASIN: {r['asin']} | Category ID: {r['category_id']}")

if __name__ == "__main__":
    verify()
