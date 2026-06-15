import os
<<<<<<< HEAD
import psycopg2
from dotenv import load_dotenv

load_dotenv()

saddl_url = os.getenv("SADDL_DATABASE_URL")
pricing_url = os.getenv("PRICING_DATABASE_URL")

def inspect_db(url, name):
    print(f"--- Inspecting {name} ---")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Check if sc_raw.competitor_pricing exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'sc_raw' 
                AND table_name = 'competitor_pricing'
            );
        """)
        exists = cur.fetchone()[0]
        print(f"sc_raw.competitor_pricing exists: {exists}")
        
        if exists:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'sc_raw'
                AND table_name = 'competitor_pricing'
                ORDER BY ordinal_position;
            """)
            cols = cur.fetchall()
            print("Columns:")
            for col in cols:
                print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
                
            # Get primary keys
            cur.execute("""
                SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type
                FROM   pg_index i
                JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                     AND a.attnum = ANY(i.indkey)
                WHERE  i.indrelid = 'sc_raw.competitor_pricing'::regclass
                AND    i.indisprimary;
            """)
            pkeys = cur.fetchall()
            print("Primary Keys:")
            for pk in pkeys:
                print(f"  {pk[0]}")
        
        # Check competitor_products schema as comparison
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'competitor_products'
            );
        """)
        comp_exists = cur.fetchone()[0]
        print(f"competitor_products exists: {comp_exists}")
        if comp_exists:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'competitor_products'
                ORDER BY ordinal_position;
            """)
            cols = cur.fetchall()
            print("competitor_products columns:")
            for col in cols:
                print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

inspect_db(saddl_url, "SADDL DB")
inspect_db(pricing_url, "Pricing DB")
=======
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
>>>>>>> 5021546c74a8a9e0d82812ff2d0468e014ba5e35
