import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('PRICING_DATABASE_URL'))
cur = conn.cursor()

# Check pb_client_listings columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'pb_client_listings'")
print('pb_client_listings columns:', [r[0] for r in cur.fetchall()])

# Check if we have any existing settings table
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%settings%'")
print('Settings tables:', [r[0] for r in cur.fetchall()])

cur.close()
conn.close()
