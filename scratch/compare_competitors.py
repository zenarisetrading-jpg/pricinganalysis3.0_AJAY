import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_supabase_client

def compare_parent_competitors():
    supabase = get_supabase_client()
    parents = ["B0BCX814PP", "B0CDGL6TZP", "B0CDJYR8QT", "B0CGXK9CWT"]
    
    print("\n--- Checking pb_client_snapshots_daily ---")
    try:
        res2 = supabase.table("pb_client_snapshots_daily").select("asin, n_competitors, floor_price, median_price, ceiling_price").in_("asin", parents).execute()
        print("Daily Snapshot entries:")
        for row in res2.data:
            print(f" - Parent: {row.get('asin')} | n_competitors: {row.get('n_competitors')} | Floor: {row.get('floor_price')} | Median: {row.get('median_price')} | Ceiling: {row.get('ceiling_price')}")
    except Exception as e:
        print(f"Error snapshots: {e}")

    print("\n--- Checking pb_recommendations ---")
    try:
        res3 = supabase.table("pb_recommendations").select("asin, recommended_price, action, reasoning").in_("asin", parents).execute()
        print("Recommendations entries:")
        for row in res3.data:
            print(f" - Parent: {row.get('asin')} | Recommended (Target): {row.get('recommended_price')} | Action: {row.get('action')} | Reasoning: {row.get('reasoning')[:150]}...")
    except Exception as e:
        print(f"Error recommendations: {e}")

if __name__ == "__main__":
    compare_parent_competitors()
