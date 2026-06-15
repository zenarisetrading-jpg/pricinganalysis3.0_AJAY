
import sys
import os
sys.path.append('.')
from db import get_supabase_client

def update_category():
    sb = get_supabase_client()
    res = sb.table('pb_client_listings').update({'category_id': '12373047031'}).eq('client_id', 'oneshot_uae').eq('asin', 'B0FNN5WKDG').execute()
    if res.data:
        print(f"SUCCESS: Updated B0FNN5WKDG to Category ID {res.data[0]['category_id']}")
    else:
        print("ERROR: No rows updated. Check ASIN and Client ID.")

if __name__ == "__main__":
    update_category()
