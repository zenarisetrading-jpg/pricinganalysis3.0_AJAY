import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

# See what tables exist with price in them
cur.execute("""
    SELECT table_schema, table_name, column_name 
    FROM information_schema.columns 
    WHERE column_name LIKE '%price%' 
    AND table_schema IN ('public', 'sc_raw', 'sc_final', 'ads')
""")
rows = cur.fetchall()
print("\nTables with 'price':")
for r in rows:
    if 'competitor_products' not in r[1] and 'pricing_analysis' not in r[1]:
        print(r)

cur.close()
conn.close()
