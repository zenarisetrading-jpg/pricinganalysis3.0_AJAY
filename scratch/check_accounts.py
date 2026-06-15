import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import fetch_saddl_accounts, fetch_account_products_with_categories, execute_saddl_query

accounts = fetch_saddl_accounts()
print(f"Found {len(accounts)} accounts:")
for acc in accounts:
    client_id = acc["client_id"]
    name = acc["client_name"]
    # Check products count
    products = fetch_account_products_with_categories(client_id)
    print(f"  Account ID: {client_id} | Name: {name} | Products Count: {len(products)}")
