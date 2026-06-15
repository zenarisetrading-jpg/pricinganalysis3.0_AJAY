import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    sb: Client = create_client(url, key)
    
    parent_asins = ["B0CGXK9CWT", "B0CDGL6TZP", "B0CDJYR8QT", "B0BCX814PP"]
    
    # 1. Fetch child listings to see saved reference names
    print("Checking reference_name in pb_client_listings for s2c_test:")
    for parent in parent_asins:
        # Find child variations from SADDL first
        from features.price_benchmarking.saddl_db import fetch_account_products_with_categories
        products = fetch_account_products_with_categories("s2c_test")
        child_asins = [p["asin"] for p in products if p["parent_asin"] == parent or p["asin"] == parent]
        
        resp = sb.table("pb_client_listings").select("asin, reference_name").in_("asin", child_asins).eq("client_id", "s2c_test").execute()
        print(f"Parent: {parent} | Children: {child_asins}")
        for item in resp.data or []:
            print(f"  - Child ASIN: {item.get('asin')} | reference_name: {item.get('reference_name')}")

if __name__ == "__main__":
    main()
