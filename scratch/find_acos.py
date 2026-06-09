import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('SADDL_DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT table_schema, table_name, column_name 
    FROM information_schema.columns 
    WHERE column_name ILIKE '%acos%' OR column_name ILIKE '%spend%' OR column_name ILIKE '%cvr%' OR column_name ILIKE '%conversion%'
    AND table_schema NOT IN ('information_schema', 'pg_catalog')
""")
print("Related columns:")
for r in cur.fetchall():
    print(r)

cur.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = 'ads'
""")
print("\nAds tables:")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
