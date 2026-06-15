import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

# Check SADDL BSR columns
conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='sc_raw' AND table_name='bsr_history' LIMIT 30")
print('BSR columns:', [r[0] for r in cur.fetchall()])

# Also check a sample row
cur.execute("SELECT * FROM sc_raw.bsr_history LIMIT 1")
cols = [d[0] for d in cur.description]
print('Sample columns:', cols)

cur.close(); conn.close()
