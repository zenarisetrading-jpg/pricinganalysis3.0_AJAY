import os
from apify_client import ApifyClient
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from features.price_benchmarking.benchmarking import compute_benchmark, CompetitorPrice
from features.price_benchmarking.recommendations import recommend, RepricingStrategy

# Load environment
load_dotenv()
token = os.getenv("APIFY_TOKEN")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def clean_production_run():
    if not token:
        print("Error: APIFY_TOKEN not found in .env")
        return

    client = ApifyClient(token)
    categories = [
        {"name": "Coffee Machines", "query": "https://www.amazon.ae/s?k=coffee+machine"},
        {"name": "Headphones", "query": "https://www.amazon.ae/s?k=noise+cancelling+headphones"},
        {"name": "Backpacks", "query": "https://www.amazon.ae/s?k=laptop+backpack"}
    ]

    actor_id = "vaclavrut/amazon-crawler"
    client_id = "s2c-uae"
    today = date.today().isoformat()
    
    for cat in categories:
        print(f"\n--- SCRAPING & ANALYZING: {cat['name']} ---")
        run_input = {
            "categoryOrProductUrls": [{"url": cat['query']}],
            "maxItems": 20,
            "proxyCountry": "AE",
            "useResidentialProxies": True
        }
        
        try:
            # 1. Scrape Live Data
            run = client.actor(actor_id).call(run_input=run_input)
            items = client.dataset(run['defaultDatasetId']).list_items().items
            
            competitors = []
            event_rows = []
            
            for item in items:
                price_val = item.get('price', {})
                price = price_val.get('value') if isinstance(price_val, dict) else None
                if not price: continue

                asin = item.get('asin')
                seller = item.get('sellerName') or "Amazon.ae"
                
                # Prepare Raw Event (Tier 1)
                event_rows.append({
                    "asin": asin,
                    "marketplace": "UAE",
                    "event_type": "poll",
                    "floor_price": price,
                    "buy_box_price": price,
                    "seller_name": seller,
                    "category_name": cat['name'],
                    "created_at": datetime.now().isoformat()
                })
                
                # For Analysis
                competitors.append(CompetitorPrice(asin=asin, title=item.get('title', 'Unknown'), price=price, is_fba=True))

            # 2. Save Raw Events
            if event_rows:
                supabase.table("pb_price_events").insert(event_rows).execute()
                print(f"Saved {len(event_rows)} Raw Events for {cat['name']}")

            # 3. Create a SADDL Product for this category and Analyze (Tier 3)
            if competitors:
                # Find median to set a "Smart" price for ourselves
                prices = sorted([c.price for c in competitors])
                median = prices[len(prices)//2]
                your_asin = f"SADDL-{cat['name'].split()[0].upper()}-PRO"
                your_price = round(median * 1.1, 2) # Be slightly premium (10% higher)

                # Calculate Benchmark
                benchmark = compute_benchmark(
                    sku_id=f"SKU-{cat['name'].split()[0].upper()}",
                    asin=your_asin,
                    your_price=your_price,
                    competitors=competitors,
                    marketplace="UAE"
                )
                rec = recommend(benchmark, strategy=RepricingStrategy.MID)

                # Save Snapshot
                supabase.table("pb_client_snapshots_daily").insert({
                    "client_id": client_id, "sku_id": f"SKU-{cat['name'].split()[0].upper()}",
                    "asin": your_asin, "snapshot_date": today, "your_price": your_price,
                    "n_competitors": len(competitors), "floor_price": benchmark.floor,
                    "ceiling_price": benchmark.ceiling, "median_price": benchmark.median,
                    "p25_price": benchmark.p25, "p75_price": benchmark.p75,
                    "percentile_rank": benchmark.percentile_rank, "index_vs_median": benchmark.index_vs_median,
                    "zone": benchmark.zone.value, "strategy": "mid"
                }).execute()

                # Save Recommendation
                supabase.table("pb_recommendations").insert({
                    "client_id": client_id, "asin": your_asin, "sku_id": f"SKU-{cat['name'].split()[0].upper()}",
                    "marketplace": "UAE", "strategy": "mid", "current_price": your_price,
                    "recommended_price": rec.recommended_price, "action": rec.action,
                    "confidence": "high", "reasoning": rec.reasoning, "snapshot_date": today
                }).execute()

                # Save Performance (Audit Tab)
                perf_rows = []
                for i in range(7):
                    d = (date.today() - timedelta(days=i)).isoformat()
                    perf_rows.append({
                        "client_id": client_id, "asin": your_asin, "marketplace": "UAE",
                        "performance_date": d, "units_ordered": 10 + i, "sessions": 300 + (i*10),
                        "acos": 12.0 + i, "cvr": 0.05
                    })
                supabase.table("pb_client_performance_daily").insert(perf_rows).execute()

                print(f"Analysis Complete for {cat['name']}! (ASIN: {your_asin})")

        except Exception as e:
            print(f"Error processing {cat['name']}: {e}")

if __name__ == "__main__":
    clean_production_run()
