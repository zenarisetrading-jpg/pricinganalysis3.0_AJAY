import os
from dotenv import load_dotenv
import sys
sys.path.append('d:/pricing_analysis')
from features.price_benchmarking.saddl_db import fetch_saddl_categories

load_dotenv('d:/pricing_analysis/.env')

cats = fetch_saddl_categories("s2c_test")
for c in cats:
    print(f"{c['category_name']}: {c['asin_count']}")
