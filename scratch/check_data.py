import os
import sys
from dotenv import load_dotenv

# Add parent dir to path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import get_supabase_client

load_dotenv()

def find_data():
    supabase = get_supabase_client()
    
    # Try to find any products in any of the benchmarking tables
    tables = ["pb_benchmarking_skus", "pb_category_competitors", "pb_price_events"]
    
    for t in tables:
        try:
            res = supabase.table(t).select("*").limit(10).execute()
            print(f"Table {t}: {len(res.data)} rows")
            for row in res.data:
                print(f"  Row: {row}")
        except Exception as e:
            print(f"Error on {t}: {e}")

    # Try to find accounts in pb_clients
    try:
        res = supabase.table("pb_clients").select("*").execute()
        print(f"Clients: {len(res.data)}")
        for row in res.data:
            print(f"  Client: {row}")
    except Exception as e:
        print(f"Error on pb_clients: {e}")

if __name__ == "__main__":
    find_data()
