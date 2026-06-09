import os
from dotenv import load_dotenv
import sys
from supabase import create_client, Client
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import execute_saddl_query

load_dotenv('d:/pricing_analysis/.env')

rows = execute_saddl_query("SELECT DISTINCT category_name FROM sc_raw.bsr_history WHERE account_id = 's2c_test'")
print("Categories in saddl_db:")
for r in rows:
    print(r[0])
