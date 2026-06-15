
import sys
import os
sys.path.append('.')
from features.price_benchmarking.saddl_db import execute_saddl_query

def check():
    query = "SELECT report_date, units_ordered, sessions FROM sc_raw.sales_traffic WHERE child_asin = 'B0DGLGPN1N' AND account_id = 'oneshot_uae' ORDER BY report_date DESC LIMIT 5"
    res = execute_saddl_query(query)
    print("--- LATEST ENTRIES IN SALES_TRAFFIC ---")
    for r in res:
        print(f"Date: {r[0]} | Orders: {r[1]} | Sessions: {r[2]}")

if __name__ == "__main__":
    check()
