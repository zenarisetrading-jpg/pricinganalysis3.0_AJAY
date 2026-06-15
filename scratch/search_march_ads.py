import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asin = 'B0DGLGPN1N'

print(f"Checking ads.product_stats for {asin} in March 2026...")
cur.execute("""
    SELECT date, spend, sales 
    FROM ads.product_stats 
    WHERE asin = %s
    AND date >= '2026-03-01' AND date <= '2026-03-31'
    ORDER BY date
""", (asin,))
rows = cur.fetchall()
for r in rows:
    print(r)

cur.close()
conn.close()
