import sys
sys.path.insert(0, '.')
from db import get_supabase_client
sb = get_supabase_client()

PARENT_ASINS = [
    'B0FM45GBTY', 'B0FM43BSB2', 'B0DLXPQZCJ',
    'B0DLX4FKPT', 'B0DLX3Y8JN', 'B0DLX3GJNJ',
    'B0DGLGPN1N', 'B0FNN5WKDG'
]

KEYWORD = 'electrolyte'

print(f"{'Parent ASIN':<15} {'Total Pool':>12} {'After Filter':>14} {'Min Price':>10} {'Max Price':>10} {'Median':>10} {'P25':>10} {'P75':>10}")
print("-" * 100)

for parent in PARENT_ASINS:
    res = sb.table('competitor_products').select('competitor_asin,competitor_title,competitor_price').eq('parent_asin', parent).execute()
    all_comps = res.data or []
    
    # Apply keyword filter (same logic as backend LIKE '%electrolyte%')
    filtered = [
        c for c in all_comps
        if KEYWORD.lower() in (c.get('competitor_title') or '').lower()
    ]
    
    prices = sorted([
        float(c['competitor_price']) for c in filtered
        if c.get('competitor_price') is not None
    ])
    
    total_pool = len(all_comps)
    after_filter = len(filtered)
    min_p = prices[0] if prices else 0
    max_p = prices[-1] if prices else 0
    
    n = len(prices)
    median = prices[n // 2] if prices else 0
    p25 = prices[int(n * 0.25)] if prices else 0
    p75 = prices[int(n * 0.75)] if prices else 0

    print(f"{parent:<15} {total_pool:>12} {after_filter:>14} {min_p:>10.2f} {max_p:>10.2f} {median:>10.2f} {p25:>10.2f} {p75:>10.2f}")
