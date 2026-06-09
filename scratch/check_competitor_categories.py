import os, sys
sys.path.insert(0, '.')
from db import get_supabase_client
from features.price_benchmarking.saddl_db import execute_saddl_query

sb = get_supabase_client()

# Get all competitor ASINs for this parent
res = sb.table('competitor_products').select('competitor_asin,competitor_title').eq('parent_asin', 'B0FNN5WKDG').execute()
comp_asins = [r['competitor_asin'] for r in res.data]
print(f"Total competitors for B0FNN5WKDG: {len(comp_asins)}")
print(f"Sample ASINs: {comp_asins[:5]}")

# Check category names from bsr_history
if comp_asins:
    placeholders = ','.join([f"'{a}'" for a in comp_asins[:200]])
    q = f"""
        SELECT DISTINCT category_name, COUNT(*) as product_count
        FROM sc_raw.bsr_history
        WHERE asin IN ({placeholders})
        GROUP BY category_name
        ORDER BY product_count DESC
        LIMIT 20
    """
    rows = execute_saddl_query(q)
    print("\nCategory names in bsr_history for these competitors:")
    for r in rows:
        print(r)
