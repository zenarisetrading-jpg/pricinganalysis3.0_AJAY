import sys
import json
sys.path.insert(0, '.')
from db import get_supabase_client

def simulate_ui():
    sb = get_supabase_client()
    # Fetch recommendation for s2c_test
    res = sb.table('pb_recommendations').select('metadata').eq('client_id', 's2c_test').eq('asin', 'B0FWKSMV4J').execute()
    if not res.data:
        print("Recommendation not found for s2c_test / B0FWKSMV4J")
        return
        
    meta = res.data[0].get('metadata') or {}
    competitors = meta.get('competitors') or []
    print(f"Loaded {len(competitors)} competitors.")
    
    # Let's extract prices
    prices = []
    for c in competitors:
        p = float(c.get('price', 0))
        if p > 0:
            prices.append(p)
            
    if not prices:
        print("No competitor prices found.")
        return
        
    min_val = min(prices)
    max_val = max(prices)
    print(f"Prices: min={min_val}, max={max_val}")
    
    # Binning parameters
    bin_count = 10
    bin_width = (max_val - min_val) / bin_count
    
    bins = []
    for i in range(bin_count):
        start = min_val + i * bin_width
        end = start + bin_width
        bins.append({
            "start": start,
            "end": end,
            "competitors": []
        })
        
    # Assign competitors to bins
    for c in competitors:
        p = float(c.get('price', 0))
        clamped_p = max(min_val, min(max_val, p))
        assigned = False
        for i in range(bin_count):
            is_last = (i == bin_count - 1)
            if clamped_p >= bins[i]["start"] and (clamped_p <= bins[i]["end"] if is_last else clamped_p < bins[i]["end"]):
                bins[i]["competitors"].append(c)
                assigned = True
                break
                
    # Group and count brands per bin
    for idx, b in enumerate(bins):
        if not b["competitors"]:
            continue
            
        brand_counts = {}
        for c in b["competitors"]:
            brand_raw = c.get("brand") or ""
            if brand_raw in ('None', 'null', 'NULL'):
                brand_raw = ""
            if not brand_raw or brand_raw.strip() == "":
                title_words = [w for w in (c.get("title") or "Unknown Brand").split(" ") if w.strip() != ""]
                brand_raw = " ".join(title_words[:2])
                
            brand = brand_raw.strip().title() # close enough to JS behavior
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
            
        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        print(f"\nBin {idx+1} [AED {b['start']:.1f} - {b['end']:.1f}]:")
        print(f"  Total competitors in bin: {len(b['competitors'])}")
        print("  Top Brands:")
        for brand, count in sorted_brands[:4]:
            print(f"    • {brand}: {count}")
        if len(sorted_brands) > 4:
            print(f"    + {len(sorted_brands) - 4} more brands")

if __name__ == '__main__':
    simulate_ui()
