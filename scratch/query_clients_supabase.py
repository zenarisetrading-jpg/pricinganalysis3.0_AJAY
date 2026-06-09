import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return
        
    sb: Client = create_client(url, key)
    print("--- ACTIVE CLIENTS IN SUPABASE (pb_clients) ---")
    try:
        resp = sb.table("pb_clients").select("*").execute()
        if resp.data:
            for c in resp.data:
                print(f"ID: {c.get('client_id')} | Name: {c.get('name')} | Marketplace: {c.get('marketplace')} | Active: {c.get('is_active')}")
        else:
            print("No clients found in pb_clients table.")
    except Exception as e:
        print(f"Error querying pb_clients: {e}")

if __name__ == "__main__":
    main()
