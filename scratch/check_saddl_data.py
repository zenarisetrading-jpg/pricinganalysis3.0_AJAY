import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asins = ['B0FNN5WKDG','B0DGLGPN1N','B0DLX3GJNJ','B0DLX3Y8JN','B0DLX4FKPT','B0DLXPQZCJ','B0FM43BSB2','B0FM45GBTY','B0CZLK598D','B0CZLKLJX5','B0D39R47CC','B0DGLCG5G1','B0DGLD7P83','B0DGLHDFPK','B0F6NHKSQ1','B0FFB2F46C','B0FM469PMF','B0FMYLRD2X']
placeholders = ', '.join(['%s'] * len(asins))

print("Checking sc_raw.fba_inventory for any rows:")
cur.execute(f"SELECT asin, your_price, client_id, snapshot_date FROM sc_raw.fba_inventory WHERE asin IN ({placeholders}) ORDER BY snapshot_date DESC LIMIT 10", asins)
for r in cur.fetchall(): print(r)

print("\nChecking sc_raw.sales_traffic for ordered_revenue and units_ordered:")
cur.execute(f"""
    SELECT child_asin, ordered_revenue, units_ordered, report_date 
    FROM sc_raw.sales_traffic 
    WHERE child_asin IN ({placeholders}) 
    AND ordered_revenue > 0 AND units_ordered > 0
    ORDER BY report_date DESC LIMIT 20
""", asins)
for r in cur.fetchall(): print(r)

cur.close()
conn.close()
