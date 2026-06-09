import sys
import os
sys.path.append(os.getcwd())
from db import get_supabase_client

def count_oneshot_skus():
    s = get_supabase_client()
    client_id = "oneshot_uae"
    
    # Check total SKUs linked
    res = s.table("pb_benchmarking_skus").select("count", count="exact").eq("client_id", client_id).execute()
    print(f"\n📦 Total products linked to {client_id}: {res.count}")

if __name__ == "__main__":
    count_oneshot_skus()
