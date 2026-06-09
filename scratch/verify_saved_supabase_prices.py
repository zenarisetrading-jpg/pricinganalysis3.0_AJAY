import sys
import os
sys.path.insert(0, '.')

from db import get_supabase_client

def main():
    sb = get_supabase_client()
    resp = sb.table("pb_recommendations").select("parent_asin, current_price").eq("client_id", "oneshot_uae").execute()
    data = resp.data or []
    
    print("\nSupabase saved current prices for Parent ASIN recommendations:")
    print(f"{'Parent ASIN':<15} | {'Saved Current Price':<20}")
    print("-" * 40)
    for row in sorted(data, key=lambda x: x["parent_asin"]):
        print(f"{row['parent_asin']:<15} | {row['current_price']:<20}")

if __name__ == "__main__":
    main()
