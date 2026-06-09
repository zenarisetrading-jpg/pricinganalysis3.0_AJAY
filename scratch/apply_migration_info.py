import os
from db import get_supabase_client

def apply_migration():
    sb = get_supabase_client()
    migration_path = "supabase/migrations/20260510000000_create_discovery_tables.sql"
    
    if not os.path.exists(migration_path):
        print(f"Migration file not found: {migration_path}")
        return

    with open(migration_path, "r") as f:
        sql = f.read()

    print("Attempting to apply migration via RPC...")
    try:
        # Supabase doesn't have a direct 'execute_sql' but sometimes 'exec_sql' is enabled as an RPC
        # If not, I'll have to create the tables one by one using a different method
        # or just tell the user to run it in the SQL Editor.
        # Let's try to create them via the 'rpc' if it exists.
        # Actually, let's try a safer way: check if I can just use the supabase client to create tables?
        # No, supabase-py doesn't support DDL.
        
        # I'll try to run a dummy query to see if I can at least reach the DB.
        sb.table("pb_price_events").select("id").limit(1).execute()
        print("Connected to Supabase.")
        
        print("\n--- ACTION REQUIRED ---")
        print("I have created the migration file at:")
        print(migration_path)
        print("\nPlease copy the content of this file and run it in your Supabase SQL Editor.")
        print("I cannot apply DDL (table creation) directly via the current API client.")
        print("------------------------\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_migration()
