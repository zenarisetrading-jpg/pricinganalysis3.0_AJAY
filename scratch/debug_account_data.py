import os
from features.price_benchmarking.saddl_db import execute_saddl_query

def debug_data():
    account_id = "oneshot-uae"
    print(f"Checking data for account: {account_id}")
    
    # 1. Check if account exists at all
    query1 = "SELECT count(*) FROM sc_raw.bsr_history WHERE account_id = %s"
    row1 = execute_saddl_query(query1, (account_id,))
    print(f"Total rows in bsr_history: {row1[0][0] if row1 else 0}")
    
    # 2. Check latest report date
    query2 = "SELECT MAX(report_date) FROM sc_raw.bsr_history WHERE account_id = %s"
    row2 = execute_saddl_query(query2, (account_id,))
    print(f"Latest report date for this account: {row2[0][0] if row2 else 'None'}")
    
    # 3. Check overall latest report date
    query3 = "SELECT MAX(report_date) FROM sc_raw.bsr_history"
    row3 = execute_saddl_query(query3)
    print(f"Overall latest report date in table: {row3[0][0] if row3 else 'None'}")

if __name__ == "__main__":
    debug_data()
