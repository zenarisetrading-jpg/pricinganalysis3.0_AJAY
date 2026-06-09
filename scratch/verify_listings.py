import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_supabase_client

def main():
    sb = get_supabase_client()
    
    # Check pb_client_listings for oneshot_uae
    print("listings in pb_client_listings for oneshot_uae:")
    list_resp = sb.table("pb_client_listings").select("*").eq("client_id", "oneshot_uae").execute()
    for row in list_resp.data:
        print(f"ASIN: {row['asin']}, Category: {row.get('category_id')}, Status: {row.get('status')}")

if __name__ == "__main__":
    main()
