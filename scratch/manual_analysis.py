import os
import json
from datetime import date, timedelta
from apify_client import ApifyClient
from dotenv import load_dotenv
from supabase import create_client, Client
from features.price_benchmarking.benchmarking import compute_benchmark, CompetitorPrice
from features.price_benchmarking.recommendations import recommend, RepricingStrategy

# Load environment
load_dotenv()
token = os.getenv("APIFY_TOKEN")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Initialize Supabase
supabase: Client = create_client(supabase_url, supabase_key)

def run_full_test_analysis(target_asin, your_price, client_id="s2c-uae", marketplace="UAE"):
    print(f"--- FULL SYSTEM TEST ANALYSIS ---")
    print(f"Target: {target_asin} | Client: {client_id}")

    # 1. Competitor Data
    competitors = [
        CompetitorPrice(asin="COMP1", title="Market Seller A", price=your_price - 50, is_fba=True),
        CompetitorPrice(asin="COMP2", title="Market Seller B", price=your_price - 100, is_fba=True),
        CompetitorPrice(asin="COMP3", title="Market Seller C", price=your_price + 20, is_fba=False),
        CompetitorPrice(asin="COMP4", title="Market Seller D", price=your_price - 10, is_fba=True),
    ]

    # 2. Benchmarking
    benchmark = compute_benchmark(
        sku_id=f"SKU-{target_asin}",
        asin=target_asin,
        your_price=float(your_price),
        competitors=competitors,
        marketplace=marketplace
    )

    if not benchmark:
        print("Benchmarking failed.")
        return

    # 3. Recommendation
    rec = recommend(
        benchmark, 
        strategy=RepricingStrategy.MID,
        min_price=your_price - 500,
        max_price=your_price + 500
    )

    # 4. SAVE TO ALL TIERS (FOR ALL TABS)
    print("\nStep 4: Pushing data to ALL tables for full UI testing...")
    
    try:
        today_iso = date.today().isoformat()

        # A. BENCHMARKING & OVERVIEW TABS
        snapshot_row = {
            "client_id": client_id,
            "sku_id": f"SKU-{target_asin}",
            "asin": target_asin,
            "snapshot_date": today_iso,
            "your_price": your_price,
            "n_competitors": len(competitors),
            "floor_price": benchmark.floor,
            "ceiling_price": benchmark.ceiling,
            "median_price": benchmark.median,
            "p25_price": benchmark.p25,
            "p75_price": benchmark.p75,
            "percentile_rank": benchmark.percentile_rank,
            "index_vs_median": benchmark.index_vs_median,
            "zone": benchmark.zone.value,
            "strategy": "mid"
        }
        supabase.table("pb_client_snapshots_daily").upsert(snapshot_row, on_conflict="client_id,asin,snapshot_date").execute()
        
        supabase.table("pb_recommendations").insert({
            "client_id": client_id,
            "asin": target_asin,
            "sku_id": f"SKU-{target_asin}",
            "marketplace": marketplace,
            "strategy": "mid",
            "current_price": your_price,
            "recommended_price": rec.recommended_price,
            "action": rec.action,
            "confidence": rec.confidence.value,
            "reasoning": rec.reasoning,
            "snapshot_date": today_iso
        }).execute()

        # B. ALERTS TAB
        supabase.table("pb_alerts").insert({
            "client_id": client_id,
            "asin": target_asin,
            "sku_id": f"SKU-{target_asin}",
            "marketplace": marketplace,
            "alert_type": "price_gap_widening",
            "severity": "medium",
            "title": f"Market Position Shift for {target_asin}",
            "message": f"Your price is now {benchmark.index_vs_median:.1f}% vs market median.",
            "action_hint": "Consider adjusting to Target Price",
            "metadata": {"zone": benchmark.zone.value}
        }).execute()

        # C. AUDIT TAB
        perf_rows = []
        for i in range(3):
            d = (date.today() - timedelta(days=i)).isoformat()
            perf_rows.append({
                "client_id": client_id,
                "asin": target_asin,
                "marketplace": marketplace,
                "performance_date": d,
                "units_ordered": 10 + i,
                "sessions": 200 + (i * 10),
                "acos": 25.5 + i,
                "cvr": 0.05
            })
        supabase.table("pb_client_performance_daily").upsert(perf_rows, on_conflict="client_id,asin,marketplace,performance_date").execute()

        print("\nSUCCESS: ALL TABS UPDATED!")
        print(f"Overview, Benchmarking, Alerts, and Audit tabs are now ready.")
        print(f"URL: http://localhost:8000/benchmarking")
        
    except Exception as e:
        print(f"Error saving to Supabase: {e}")

if __name__ == "__main__":
    run_full_test_analysis(target_asin="B09G96TFF7", your_price=2100.0)
