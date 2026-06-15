import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

asin = 'B0DGLGPN1N'
date = '2026-03-12'

print(f"Checking sales_traffic for {asin} on {date}...")
cur.execute("""
    SELECT child_asin, parent_asin, units_ordered, sessions, unit_session_percentage 
    FROM sc_raw.sales_traffic 
    WHERE (child_asin = %s OR parent_asin = %s)
    AND report_date = %s
""", (asin, asin, date))
rows = cur.fetchall()
for r in rows:
    print(r)

cur.close()
conn.close()
