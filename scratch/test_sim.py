
import os
from datetime import date
from dotenv import load_dotenv
from db import get_supabase_client
from features.price_benchmarking.snapshot_service import calculate_benchmarks_for_client

load_dotenv()
supabase = get_supabase_client()

print("Testing calculate_benchmarks_for_client...")
market_prices_override = {
    "B07P7MZG97": {"price": 45.99, "is_buy_box_winner": True}
}

try:
    results = calculate_benchmarks_for_client(
        supabase=supabase,
        client_id="oneshot_uae",
        marketplace="UAE",
        market_prices_override=market_prices_override,
        persist=False
    )
    print("Success!")
    print(f"Snapshots: {len(results['snapshots'])}")
except Exception as e:
    print(f"Error: {e}")
