import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('PRICING_DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT pg_get_constraintdef(c.oid) 
    FROM pg_constraint c 
    JOIN pg_class t ON c.conrelid = t.oid 
    WHERE t.relname = 'pb_recommendations' 
    AND c.conname = 'pb_recommendations_action_check'
""")
print(cur.fetchone())

cur.close()
conn.close()
