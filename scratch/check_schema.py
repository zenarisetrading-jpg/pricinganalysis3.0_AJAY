import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('d:/pricing_analysis/.env')
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

res = supabase.table("pb_client_snapshots_daily").select("*").limit(1).execute()
if res.data:
    print(res.data[0].keys())
else:
    print("No data")
