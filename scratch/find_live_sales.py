import os
import sys
from dotenv import load_dotenv

# Add parent dir to path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import get_supabase_client

load_dotenv()

def find_live_sales():
    supabase = get_supabase_client()
    
    print("--- ALL CLIENTS ---")
    try:
        clients = supabase.table("pb_clients").select("*").execute()
        if not clients.data:
            print("No clients found at all.")
        for client in clients.data:
            print(f"ID: {client['client_id']} | Name: {client['name']} | Marketplace: {client['marketplace']} | Active: {client['is_active']}")
    except Exception as e:
        print(f"Error fetching clients: {e}")

    print("\n--- ALL SKUS ---")
    try:
        skus = supabase.table("pb_benchmarking_skus").select("*").execute()
        if not skus.data:
            print("No SKUs found.")
        for sku in skus.data:
            print(f"ASIN: {sku['asin']} | SKU: {sku['sku_id']} | Client: {sku['client_id']} | Title: {sku['product_title']}")
    except Exception as e:
        print(f"Error fetching skus: {e}")

if __name__ == "__main__":
    find_live_sales()
