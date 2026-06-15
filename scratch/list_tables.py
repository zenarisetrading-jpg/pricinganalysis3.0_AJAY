import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

# Find all tables in sc_raw and sc_final
cur.execute("""
    SELECT table_schema, table_name 
    FROM information_schema.tables 
    WHERE table_schema IN ('public', 'sc_raw', 'sc_final')
    ORDER BY table_schema, table_name
""")
rows = cur.fetchall()
print("Tables:")
for r in rows:
    print(r)

cur.close()
conn.close()
