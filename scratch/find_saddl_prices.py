import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asins = ['B0FNN5WKDG','B0DGLGPN1N','B0DLX3GJNJ','B0DLX3Y8JN','B0DLX4FKPT','B0DLXPQZCJ','B0FM43BSB2','B0FM45GBTY','B0CZLK598D','B0CZLKLJX5','B0D39R47CC','B0DGLCG5G1','B0DGLD7P83','B0DGLHDFPK','B0F6NHKSQ1','B0FFB2F46C','B0FM469PMF','B0FMYLRD2X']
placeholders = ', '.join(['%s'] * len(asins))

print("Checking sc_raw.fba_inventory")
cur.execute(f"SELECT asin, your_price, client_id FROM sc_raw.fba_inventory WHERE asin IN ({placeholders}) LIMIT 10", asins)
for r in cur.fetchall(): print(r)

print("\nChecking sc_raw.sales_traffic")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='sc_raw' AND table_name='sales_traffic' AND column_name LIKE '%price%'")
for r in cur.fetchall(): print(r)

print("\nChecking public.competitor_products")
cur.execute(f"SELECT parent_asin, competitor_asin, competitor_price FROM public.competitor_products WHERE competitor_asin IN ({placeholders}) LIMIT 10", asins)
for r in cur.fetchall(): print(r)

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
