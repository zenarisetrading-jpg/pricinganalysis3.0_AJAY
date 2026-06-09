from db import get_supabase_client
import sys

def check_tables():
    sb = get_supabase_client()
    tables = ['competitor_products', 'pricing_analysis', 'pb_price_events', 'pb_client_snapshots_daily']
    for table in tables:
        try:
            res = sb.table(table).select('id', count='exact').limit(0).execute()
            count = res.count if hasattr(res, 'count') else len(res.data)
            print(f"Table '{table}': {count} rows found.")
        except Exception as e:
            print(f"Table '{table}': Error or missing ({e})")

if __name__ == "__main__":
    check_tables()
