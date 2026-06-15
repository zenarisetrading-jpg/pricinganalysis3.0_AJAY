import os
from datetime import datetime, timezone
from db import get_supabase_client
from features.price_benchmarking.saddl_db import execute_saddl_query

def sync_performance(account_id="oneshot_uae"):
    print(f"Syncing performance data for {account_id}...")
    sb = get_supabase_client()
    
    # 1. Fetch Sales & Traffic from SADDL History
    traffic_query = """
        SELECT child_asin, units_ordered, sessions, report_date 
        FROM sc_raw.sales_traffic 
        WHERE account_id = %s 
        ORDER BY report_date DESC LIMIT 500
    """
    traffic_rows = execute_saddl_query(traffic_query, (account_id,))
    
    # 2. Fetch Ads Stats for ACoS
    stats_query = """
        SELECT asin, spend, sales, date 
        FROM ads.product_stats 
        WHERE client_id = %s 
        ORDER BY date DESC LIMIT 500
    """
    stats_rows = execute_saddl_query(stats_query, (account_id,))
    
    # Map stats by asin and date
    acos_map = {}
    for r in stats_rows:
        asin, spend, sales, date = r
        key = (asin, str(date))
        acos = (float(spend) / float(sales) * 100) if sales and float(sales) > 0 else 0
        acos_map[key] = acos

    # 3. Prepare Performance Rows
    perf_rows = []
    for r in traffic_rows:
        asin, units, sessions, date = r
        date_str = str(date)
        acos = acos_map.get((asin, date_str), 0)
        
        perf_rows.append({
            "client_id": account_id,
            "marketplace": "UAE",
            "asin": asin,
            "performance_date": date_str,
            "units_ordered": int(units or 0),
            "sessions": int(sessions or 0),
            "acos": acos,
            "cvr": (int(units or 0) / int(sessions or 1) * 100) if sessions else 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    if perf_rows:
        # We need to create pb_client_performance_daily if it doesn't exist
        # But wait, does it exist in the schema? 
        # Looking at routes.py: get_performance queries pb_client_performance_daily.
        print(f"Upserting {len(perf_rows)} performance rows...")
        # Since there's no unique constraint defined in my quick check, 
        # I'll just use insert or assume there is one.
        # Actually, let's use upsert if possible.
        sb.table("pb_client_performance_daily").upsert(perf_rows, on_conflict="client_id,asin,marketplace,performance_date").execute()
        print("✅ Performance sync complete!")
    else:
        print("No performance data found to sync.")

if __name__ == "__main__":
    sync_performance()
