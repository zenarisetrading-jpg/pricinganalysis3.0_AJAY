
import os
from features.price_benchmarking.saddl_db import execute_saddl_query
from db import get_supabase_client

supabase = get_supabase_client()

def inspect_db():
    print("--- Inspecting SADDL sc_raw.sales_traffic columns ---")
    cols = execute_saddl_query("SELECT column_name FROM information_schema.columns WHERE table_schema = 'sc_raw' AND table_name = 'sales_traffic'", [])
    print([c[0] for c in cols])

    print("\n--- Inspecting pb_client_performance_daily columns ---")
    try:
        res = supabase.table("pb_client_performance_daily").select("*").limit(1).execute()
        if res.data:
            print(res.data[0].keys())
        else:
            print("Table is empty, can't infer columns from data.")
    except Exception as e:
        print(f"Error checking local table: {e}")

if __name__ == "__main__":
    inspect_db()
