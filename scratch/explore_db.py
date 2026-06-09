import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def main():
    client = get_supabase_client()
    
    print("--- Querying public.accounts ---")
    try:
        res = client.table("accounts").select("*").execute()
        print(f"Data: {res.data}")
    except Exception as e:
        print(f"Error querying accounts: {e}")

    print("\n--- Querying public.pb_clients ---")
    try:
        res = client.table("pb_clients").select("*").execute()
        print(f"Data: {res.data}")
    except Exception as e:
        print(f"Error querying pb_clients: {e}")

if __name__ == "__main__":
    main()
