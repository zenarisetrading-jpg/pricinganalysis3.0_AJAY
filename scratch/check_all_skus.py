import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('d:/pricing_analysis/.env')
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

res = supabase.table("pb_benchmarking_skus").select("*").eq("client_id", "s2c_test").execute()
print(f"Total skus in pb_benchmarking_skus for s2c_test: {len(res.data)}")
