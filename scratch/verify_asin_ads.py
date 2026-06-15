import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asin = 'B0DGLGPN1N'
date = '2026-03-12'

print(f"Checking ads.product_stats for {asin} on {date}...")
cur.execute("""
    SELECT asin, spend, sales 
    FROM ads.product_stats 
    WHERE asin = %s
    AND date = %s
""", (asin, date))
rows = cur.fetchall()
for r in rows:
    print(r)

cur.close()
conn.close()
