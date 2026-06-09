import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

children = ["B0DGLCG5G1", "B0DGLD7P83", "B0DGLHDFPK"]
placeholders = ','.join(['%s'] * len(children))
date = '2026-03-12'

print(f"Checking ads.product_stats for children on {date}...")
cur.execute(f"""
    SELECT asin, spend, sales 
    FROM ads.product_stats 
    WHERE asin IN ({placeholders})
    AND date = %s
""", tuple(children + [date]))
rows = cur.fetchall()
for r in rows:
    print(r)

cur.close()
conn.close()
