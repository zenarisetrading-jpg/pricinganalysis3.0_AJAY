import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('d:/pricing_analysis/.env')

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")
conn = psycopg2.connect(SADDL_DATABASE_URL, options="-c default_transaction_read_only=on")
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(DISTINCT asin) 
    FROM sc_raw.bsr_history 
    WHERE account_id = 's2c_test' 
      AND report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
""")
count_max_date = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT asin) 
    FROM sc_raw.bsr_history 
    WHERE account_id = 's2c_test'
""")
count_all_time = cur.fetchone()[0]

print(f"s2c_test - MAX date count: {count_max_date}, All time count: {count_all_time}")

cur.execute("""
    SELECT COUNT(DISTINCT asin) 
    FROM sc_raw.bsr_history 
    WHERE account_id = 's2c-uae' 
      AND report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
""")
uae_count_max_date = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT asin) 
    FROM sc_raw.bsr_history 
    WHERE account_id = 's2c-uae'
""")
uae_count_all_time = cur.fetchone()[0]

print(f"s2c-uae - MAX date count: {uae_count_max_date}, All time count: {uae_count_all_time}")
