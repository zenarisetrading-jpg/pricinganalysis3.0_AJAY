import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
from features.price_benchmarking.saddl_db import execute_saddl_query

# The 4 parent ASINs that HAD competitor data were using a DIFFERENT category_id
# Sports Water Bottles BSR: cat_id=17007680031  (NOW in bsr_history)
# But previously competitor data was scraped under a DIFFERENT node
# Let's check what category_id the old snapshots stored

# Check what category_ids are in pb_recommendations metadata for s2c_test
import os
from supabase import create_client
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
sb = create_client(url, key)

res = sb.table('pb_recommendations').select('asin, parent_asin, metadata').eq('client_id', 's2c_test').eq('status', 'pending').execute()
print("=== Recommendation metadata (category_ids used in analysis) ===")
for r in (res.data or []):
    meta = r.get('metadata') or {}
    cat_ids = meta.get('category_ids', [])
    print(f"  {r['parent_asin']} -> category_ids={cat_ids}")

# Now check what category_ids are actually in competitor_pricing for each s2c_test parent ASIN
# The issue may be that scraping used DIFFERENT node IDs (Amazon sub-category vs top-level)
print()
print("=== Does competitor_pricing have any rows with the EXACT category IDs from BSR? ===")
bsr_cat_ids = [
    '17024813031',  # Cat Scratching Pads
    '17024832031',  # Catnip Toys
    '28235324031',  # Dish Drying Mats
    '16888907031',  # Disposable Dishes
    '16621133031',  # Handheld Showers
    '26408858031',  # Insulated Bottles
    '22959836031',  # Insulated Cups & Mugs
    '49979276031',  # Kids School Water Bottles
    '16856644031',  # Shower Caddies
    '17007680031',  # Sports Water Bottles
    '16888922031',  # Tumblers & Water Glasses
    '85450664031',  # Under Sink Storage
]

for cat_id in bsr_cat_ids:
    rows = execute_saddl_query(
        "SELECT COUNT(*) FROM sc_raw.competitor_pricing WHERE category_id = %s",
        (cat_id,)
    )
    count = rows[0][0] if rows else 0
    status = "[HAS DATA]" if count > 0 else "[NO DATA ]"
    print(f"  {status} cat_id={cat_id} -> {count} rows")

# Also check if maybe the data is stored with INTEGER type vs string type
print()
print("=== Sample of category_ids in competitor_pricing (to check type/format) ===")
rows = execute_saddl_query(
    "SELECT DISTINCT category_id, pg_typeof(category_id) FROM sc_raw.competitor_pricing LIMIT 5",
    ()
)
for r in rows:
    print(f"  category_id={r[0]} type={r[1]}")
