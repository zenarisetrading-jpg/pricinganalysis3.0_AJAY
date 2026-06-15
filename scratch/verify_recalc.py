import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_supabase_client

def main():
    sb = get_supabase_client()
    resp = sb.table("pb_recommendations").select("asin, parent_asin, current_price, recommended_price, action, reasoning").eq("client_id", "s2c_test").execute()
    
    print("RECOMMENDATIONS IN DATABASE FOR CLIENT s2c_test:")
    for row in resp.data:
        print(f"ASIN: {row['asin']}, Parent: {row['parent_asin']}, Current: {row['current_price']}, Target: {row['recommended_price']}, Action: {row['action']}")
        print(f"  Reasoning: {row['reasoning']}")

if __name__ == "__main__":
    main()
