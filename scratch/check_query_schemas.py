import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'ads' AND table_name = 'product_stats'")
print('ads.product_stats columns:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'sc_raw' AND table_name = 'sales_traffic'")
print('sc_raw.sales_traffic columns:', [r[0] for r in cur.fetchall()])

cur.close()
conn.close()
