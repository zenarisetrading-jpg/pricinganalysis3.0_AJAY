import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

# Find tables with 'price' column
cur.execute("""
    SELECT table_schema, table_name, column_name 
    FROM information_schema.columns 
    WHERE column_name LIKE '%price%' 
    AND table_schema IN ('public', 'sc_raw', 'sc_final')
    LIMIT 50
""")
rows = cur.fetchall()
print("Tables with 'price' columns:")
for r in rows:
    print(r)

cur.close()
conn.close()
