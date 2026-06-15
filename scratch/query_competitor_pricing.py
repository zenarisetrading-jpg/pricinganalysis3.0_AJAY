import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
saddl_url = os.getenv("SADDL_DATABASE_URL")

conn = psycopg2.connect(saddl_url)
cur = conn.cursor()

# Get 5 sample rows from sc_raw.competitor_pricing
cur.execute("SELECT * FROM sc_raw.competitor_pricing LIMIT 5")
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()

print("Columns & Sample Data in sc_raw.competitor_pricing:")
for row in rows:
    print("-" * 40)
    for col, val in zip(cols, row):
        print(f"  {col}: {val} ({type(val).__name__})")

# Get unique values of marketplace_id and category_id/category_name
cur.execute("SELECT DISTINCT marketplace_id FROM sc_raw.competitor_pricing LIMIT 10")
marketplaces = cur.fetchall()
print("\nSample marketplaces in competitor_pricing:")
for mp in marketplaces:
    print(f"  {mp[0]}")

cur.execute("SELECT COUNT(*), MIN(report_date), MAX(report_date) FROM sc_raw.competitor_pricing")
stats = cur.fetchone()
print(f"\nTotal rows: {stats[0]}, Min Date: {stats[1]}, Max Date: {stats[2]}")

cur.close()
conn.close()
