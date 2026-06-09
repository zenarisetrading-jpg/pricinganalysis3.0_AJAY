import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asins = ['B0FNN5WKDG','B0DGLGPN1N','B0DLX3GJNJ','B0DLX3Y8JN','B0DLX4FKPT','B0DLXPQZCJ','B0FM43BSB2','B0FM45GBTY','B0CZLK598D','B0CZLKLJX5','B0D39R47CC','B0DGLCG5G1','B0DGLD7P83','B0DGLHDFPK','B0F6NHKSQ1','B0FFB2F46C','B0FM469PMF','B0FMYLRD2X']
placeholders = ', '.join(['%s'] * len(asins))

query = f"""
    SELECT asin, your_price 
    FROM sc_raw.fba_inventory 
    WHERE asin IN ({placeholders})
    AND your_price IS NOT NULL AND your_price > 0
    ORDER BY pulled_at DESC
"""
cur.execute(query, asins)
rows = cur.fetchall()

prices = {}
for row in rows:
    if row[0] not in prices:
        prices[row[0]] = float(row[1])

print(f"Found prices for {len(prices)} ASINs:")
for asin, price in prices.items():
    print(f"{asin}: {price}")

cur.close()
conn.close()
