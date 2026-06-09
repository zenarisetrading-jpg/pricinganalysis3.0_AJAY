import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
PRICING_DATABASE_URL = os.getenv("PRICING_DATABASE_URL")

conn = psycopg2.connect(PRICING_DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'competitor_products'")
cols = cur.fetchall()
print("Columns in LOCAL competitor_products:")
for c in cols:
    print(f"  {c[0]}")

cur.close()
conn.close()
