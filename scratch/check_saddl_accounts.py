import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.price_benchmarking.saddl_db import fetch_saddl_accounts

def main():
    accounts = fetch_saddl_accounts()
    print("SADDL ACCOUNTS:")
    for acc in accounts:
        print(acc)

if __name__ == "__main__":
    main()
