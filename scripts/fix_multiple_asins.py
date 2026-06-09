import os
from db import get_supabase_client
from features.price_benchmarking.saddl_db import fetch_account_products_with_categories

def fix_multiple_asins(account_id="oneshot_uae"):
    print(f"Fixing 'MULTIPLE' ASINs for {account_id}...")
    sb = get_supabase_client()
    
    # 1. Fetch products grouped by parent ASIN
    products_data = fetch_account_products_with_categories(account_id)
    if not products_data:
        print("No products found for this account.")
        return

    # Group by category
    category_to_asins = {}
    for p in products_data:
        cat_id = str(p["category_id"])
        if not cat_id: continue
        category_to_asins.setdefault(cat_id, set()).add(p["parent_asin"])

    # 2. Fetch competitors that have 'MULTIPLE' as parent_asin
    comp_resp = sb.table("competitor_products").select("*").eq("parent_asin", "MULTIPLE").execute()
    competitors = comp_resp.data
    if not competitors:
        print("No 'MULTIPLE' ASINs found to fix.")
        return
        
    print(f"Found {len(competitors)} rows with 'MULTIPLE' ASIN. Fixing...")

    # 3. Re-save them for each of our ASINs
    for c in competitors:
        cat_id = str(c["category_id"])
        parent_asins = category_to_asins.get(cat_id, [])
        
        for parent_asin in parent_asins:
            row = c.copy()
            del row["id"]
            row["parent_asin"] = parent_asin
            sb.table("competitor_products").insert(row).execute()
            
    # 4. Delete the 'MULTIPLE' rows
    sb.table("competitor_products").delete().eq("parent_asin", "MULTIPLE").execute()
    print("✅ Finished fixing ASIN links!")

if __name__ == "__main__":
    fix_multiple_asins()
