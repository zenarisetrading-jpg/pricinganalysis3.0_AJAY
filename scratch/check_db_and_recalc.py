import sys
import os

# Add root folder to python path so we can import features
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_supabase_client
from scripts.force_analysis import force_analysis

def main():
    sb = get_supabase_client()
    
    # 1. Check unique client_ids in listings
    print("Checking unique client_ids in pb_client_listings:")
    list_resp = sb.table("pb_client_listings").select("client_id").execute()
    list_clients = set(row["client_id"] for row in list_resp.data if row.get("client_id"))
    print("Listing client_ids:", list_clients)

    # 2. Check unique client_ids in recommendations
    print("\nChecking unique client_ids in pb_recommendations:")
    rec_resp = sb.table("pb_recommendations").select("client_id").execute()
    rec_clients = set(row["client_id"] for row in rec_resp.data if row.get("client_id"))
    print("Recommendation client_ids:", rec_clients)

    # 3. For each found client, force analysis recalculation
    all_clients = list_clients.union(rec_clients)
    print(f"\nAll unique clients to recalculate: {all_clients}")
    
    for client in all_clients:
        print("\n" + "="*50)
        force_analysis(client)
        print("="*50)
        
    print("\nRecalculation complete!")

if __name__ == "__main__":
    main()
