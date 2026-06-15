import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import filter_related_products
from db import get_supabase_client

sb = get_supabase_client()
listing = sb.table("pb_client_listings").select("*").eq("asin", "B0CGXK9CWT").execute().data[0]

raw_pool = fetch_competitors_by_category("17007680031", "UAE")
print(f"1. Raw deduplicated pool size: {len(raw_pool)} ASINs")

filtered_pool = filter_related_products(listing, raw_pool)
print(f"2. After relevance filter: {len(filtered_pool)} ASINs")

filtered_asins = {p["asin"] for p in filtered_pool}
raw_asins = {p["asin"] for p in raw_pool}

missing = raw_asins - filtered_asins
print(f"\n3. ASINs filtered out: {missing}")

for p in raw_pool:
    if p["asin"] in missing:
        print(f"   Filtered out ASIN: {p['asin']}, Title: {p.get('title')}, Brand: {p.get('brand')}")

print("\nListing details:")
print(f"Exclude keywords: {listing.get('exclude_keywords')}")
print(f"Reference name: {listing.get('reference_name')}")
