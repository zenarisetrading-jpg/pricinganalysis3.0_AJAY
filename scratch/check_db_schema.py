import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    sb: Client = create_client(url, key)
    
    print("--- Checking pb_clients database records ---")
    try:
        resp = sb.table("pb_clients").select("*").execute()
        if resp.data:
            for row in resp.data:
                print(f"Client: {row.get('client_id')} | Org ID: {row.get('org_id')}")
        else:
            print("No clients found.")
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n--- Checking pb_price_events first record schema ---")
    try:
        resp = sb.table("pb_price_events").select("*").limit(1).execute()
        if resp.data:
            print(f"Record columns: {list(resp.data[0].keys())}")
        else:
            print("No records in pb_price_events yet.")
    except Exception as e:
        print(f"Error checking pb_price_events: {e}")

if __name__ == "__main__":
    main()
