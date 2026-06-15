import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'sc_raw' AND table_name = 'sales_traffic'
""")
print("sales_traffic columns:")
for r in cur.fetchall():
    print(r)

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'sc_raw' AND table_name = 'fba_inventory'
""")
print("\nfba_inventory columns:")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
