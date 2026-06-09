import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    sb: Client = create_client(url, key)
    
    client_id = "s2c_test"
    print(f"--- Checking persisted scraped data for client: '{client_id}' ---")
    
    # 1. Check pb_recommendations
    try:
        resp = sb.table("pb_recommendations").select("*").eq("client_id", client_id).execute()
        print(f"\n1. pb_recommendations count: {len(resp.data)}")
        if resp.data:
            print("Sample recommendation columns:", list(resp.data[0].keys()))
            for r in resp.data[:3]:
                print(f"  Parent: {r.get('parent_asin') or r.get('asin')} | Current Price: {r.get('current_price')} | Action: {r.get('action')}")
    except Exception as e:
        print("Error checking pb_recommendations:", e)
        
    # 2. Check competitor_products for the parent ASINs of s2c_test
    try:
        # First get parent ASINs from recommendations
        parent_asins = sorted(list({r.get("parent_asin") or r.get("asin") for r in resp.data if r.get("parent_asin") or r.get("asin")}))
        print(f"\nParent ASINs under {client_id}: {parent_asins}")
        
        if parent_asins:
            resp_comp = sb.table("competitor_products").select("*").in_("parent_asin", parent_asins).execute()
            print(f"\n2. competitor_products count for these parents: {len(resp_comp.data)}")
            if resp_comp.data:
                print("Sample competitor columns:", list(resp_comp.data[0].keys()))
                print(f"Sample competitor row:")
                c = resp_comp.data[0]
                print(f"  Parent: {c.get('parent_asin')} | Competitor ASIN: {c.get('competitor_asin')} | Brand: {c.get('brand')} | Title: {c.get('competitor_title')[:50]} | Price: {c.get('competitor_price')} AED")
        else:
            print("No parent ASINs found to query competitor_products.")
    except Exception as e:
        print("Error checking competitor_products:", e)

if __name__ == "__main__":
    main()
