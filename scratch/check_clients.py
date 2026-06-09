import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_supabase_client

def main():
    sb = get_supabase_client()
    
    # 1. Print pb_clients
    print("pb_clients in Supabase:")
    clients_resp = sb.table("pb_clients").select("*").execute()
    for row in clients_resp.data:
        print(row)
        
    # 2. Print pb_recommendations client_id list
    print("\nunique client_ids in pb_recommendations:")
    recs_resp = sb.table("pb_recommendations").select("client_id").execute()
    print(set(r["client_id"] for r in recs_resp.data if r.get("client_id")))

if __name__ == "__main__":
    main()
