import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('d:/pricing_analysis/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

asins = ["B0DSG94PG1", "B0FWKLG3JJ", "B0FWKSMV4J"]
client_id = "s2c_test"

print("--- pb_benchmarking_skus ---")
for asin in asins:
    res = supabase.table("pb_benchmarking_skus").select("*").eq("client_id", client_id).eq("asin", asin).execute()
    print(f"{asin}: {len(res.data) > 0}")

print("--- pb_client_listings ---")
for asin in asins:
    res = supabase.table("pb_client_listings").select("price, listing_price").eq("client_id", client_id).eq("asin", asin).execute()
    if res.data:
        print(f"{asin}: True, price: {res.data[0]}")
    else:
        print(f"{asin}: False")

print("--- pb_client_snapshots_daily ---")
for asin in asins:
    res = supabase.table("pb_client_snapshots_daily").select("snapshot_date").eq("client_id", client_id).eq("asin", asin).execute()
    print(f"{asin}: {len(res.data)} snapshots")
