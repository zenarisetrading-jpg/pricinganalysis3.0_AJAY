"""
The SADDL DB only has 57 distinct ASINs for cat_id=17007680031.
But UI shows 179/196. The count must come from Supabase pb_price_events
or pb_category_competitors. Let's check those.
"""
import sys
sys.path.insert(0, '.')
from db import get_supabase_client

sb = get_supabase_client()

CAT_ID = "17007680031"  # Sports Water Bottles

print("=" * 70)
print("STEP A: pb_category_competitors - how many for this category?")
print("=" * 70)
try:
    resp = sb.table("pb_category_competitors").select("asin", count="exact").eq("category_id", CAT_ID).execute()
    print(f"  Total rows in pb_category_competitors for cat {CAT_ID}: {resp.count}")
    resp2 = sb.table("pb_category_competitors").select("asin", count="exact").eq("category_id", CAT_ID).eq("is_active", True).execute()
    print(f"  Active rows: {resp2.count}")
    # Show some samples
    sample = sb.table("pb_category_competitors").select("asin, marketplace, added_at, source").eq("category_id", CAT_ID).limit(5).execute()
    for r in (sample.data or []):
        print(f"    asin={r['asin']} marketplace={r.get('marketplace')} source={r.get('source')} added={r.get('added_at','')[:10]}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 70)
print("STEP B: pb_price_events - how many for cat 17007680031?")
print("=" * 70)
try:
    resp = sb.table("pb_price_events").select("asin", count="exact").eq("category_name", "Sports Water Bottles").execute()
    print(f"  Rows with category_name='Sports Water Bottles': {resp.count}")
    
    # Also check by category_id field if it exists
    resp2 = sb.table("pb_price_events").select("asin", count="exact").eq("category_id", CAT_ID).execute()
    print(f"  Rows with category_id={CAT_ID}: {resp2.count}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 70)
print("STEP C: What's stored in pb_recommendations metadata for B0CGXK9CWT?")
print("(This ASIN shows 196 competitors)")
print("=" * 70)
try:
    rec = sb.table("pb_recommendations").select("*").eq("asin", "B0CGXK9CWT").eq("status", "pending").order("created_at", desc=True).limit(1).execute()
    if rec.data:
        r = rec.data[0]
        meta = r.get("metadata") or {}
        comps = meta.get("competitors", [])
        print(f"  n_competitors in metadata: {meta.get('n_competitors')}")
        print(f"  len(competitors list):     {len(comps)}")
        print(f"  category_ids in metadata:  {meta.get('category_ids')}")
        print(f"  reasoning: {r.get('reasoning', '')}")
        # Show price range of competitors
        prices = [c.get('price', 0) for c in comps if c.get('price')]
        if prices:
            print(f"  competitor price range: {min(prices):.2f} - {max(prices):.2f}")
            print(f"  First 5 competitor ASINs: {[c.get('asin') for c in comps[:5]]}")
    else:
        print("  No record found")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 70)
print("STEP D: What's stored in pb_recommendations metadata for B0CDJYR8QT?")
print("(This ASIN shows 179 competitors)")
print("=" * 70)
try:
    rec = sb.table("pb_recommendations").select("*").eq("asin", "B0CDJYR8QT").eq("status", "pending").order("created_at", desc=True).limit(1).execute()
    if rec.data:
        r = rec.data[0]
        meta = r.get("metadata") or {}
        comps = meta.get("competitors", [])
        print(f"  n_competitors in metadata: {meta.get('n_competitors')}")
        print(f"  len(competitors list):     {len(comps)}")
        print(f"  category_ids in metadata:  {meta.get('category_ids')}")
        print(f"  reasoning: {r.get('reasoning', '')}")
        prices = [c.get('price', 0) for c in comps if c.get('price')]
        if prices:
            print(f"  competitor price range: {min(prices):.2f} - {max(prices):.2f}")
            print(f"  First 5 competitor ASINs: {[c.get('asin') for c in comps[:5]]}")
    else:
        print("  No record found")
except Exception as e:
    print(f"  Error: {e}")

print("\nDone.")
