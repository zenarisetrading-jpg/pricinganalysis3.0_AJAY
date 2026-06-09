import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_supabase_client

def main():
    sb = get_supabase_client()
    
    # Query pb_recommendations for B0BCX814PP
    print("Searching for B0BCX814PP in pb_recommendations:")
    resp = sb.table("pb_recommendations").select("*").eq("asin", "B0BCX814PP").execute()
    for row in resp.data:
        print(f"Client: {row.get('client_id')}, ASIN: {row['asin']}, Current: {row['current_price']}, Target: {row['recommended_price']}, Strategy: {row.get('strategy')}, Status: {row.get('status')}")
        print(f"  Reasoning: {row['reasoning']}")

if __name__ == "__main__":
    main()
