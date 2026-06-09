import os
from datetime import date, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from features.price_benchmarking.benchmarking import compute_benchmark, CompetitorPrice
from features.price_benchmarking.recommendations import recommend, RepricingStrategy

# Load environment
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def analyze_discovered_market(client_id="s2c-uae", marketplace="UAE"):
    print("--- ANALYZING DISCOVERED COFFEE MARKET ---")
    
    # 1. Real data from our discovery run
    competitor_data = [
        ("B09SL4VRPP", 272.0), ("B08Y7Q9DTJ", 65.0), ("B0CKF9Z67V", 229.0),
        ("B0DQJMD7WQ", 251.5), ("B019AW2OY8", 445.0), ("B0F3RFT8RX", 604.95),
        ("B0FZK8VXGV", 1099.0), ("B0CMD922SQ", 296.5), ("B072WZL4ZT", 450.95),
        ("B08B8LHLLS", 73.99)
    ]
    
    competitors = [CompetitorPrice(asin=a, title=f"Comp {a}", price=p, is_fba=True) for a, p in competitor_data]
    
    # 2. Your "Product"
    your_asin = "SADDL-COFFEE-001"
    your_price = 399.00
    print(f"Your Product: {your_asin} @ {your_price} AED")

    # 3. Calculate Benchmark
    benchmark = compute_benchmark(
        sku_id="SKU-COFFEE-1",
        asin=your_asin,
        your_price=your_price,
        competitors=competitors,
        marketplace=marketplace
    )
    
    rec = recommend(benchmark, strategy=RepricingStrategy.MID)

    # 4. Save to UI Tables
    try:
        today = date.today().isoformat()
        
        # Save Snapshot
        supabase.table("pb_client_snapshots_daily").upsert({
            "client_id": client_id,
            "sku_id": "SKU-COFFEE-1",
            "asin": your_asin,
            "snapshot_date": today,
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
        }, on_conflict="client_id,asin,snapshot_date").execute()

        # Save Recommendation
        supabase.table("pb_recommendations").insert({
            "client_id": client_id, "asin": your_asin, "sku_id": "SKU-COFFEE-1",
            "marketplace": marketplace, "strategy": "mid", "current_price": your_price,
            "recommended_price": rec.recommended_price, "action": rec.action,
            "confidence": "high", "reasoning": rec.reasoning, "snapshot_date": today
        }).execute()

        # Save Performance (Audit Tab)
        perf_rows = []
        for i in range(5):
            d = (date.today() - timedelta(days=i)).isoformat()
            perf_rows.append({
                "client_id": client_id, "asin": your_asin, "marketplace": marketplace,
                "performance_date": d, "units_ordered": 5 + i, "sessions": 150 + (i*5),
                "acos": 15.0 + i, "cvr": 0.04
            })
        supabase.table("pb_client_performance_daily").upsert(perf_rows, on_conflict="client_id,asin,marketplace,performance_date").execute()

        print("\nSUCCESS: Coffee Market Analysis is live in UI!")
        print("Go to: http://localhost:8000/benchmarking")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_discovered_market()
