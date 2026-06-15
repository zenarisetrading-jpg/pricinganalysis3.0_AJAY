import os
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
