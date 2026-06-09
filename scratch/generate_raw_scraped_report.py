import os
import sys
from dotenv import load_dotenv

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_supabase_client

def main():
    try:
        # Load environment variables
        load_dotenv()
        
        supabase = get_supabase_client()
        
        # 1. Fetch the latest scraped_at timestamp from pb_price_events
        print("Finding the latest scrape event in pb_price_events...")
        latest_ts_resp = supabase.table("pb_price_events") \
            .select("created_at") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
            
        if not latest_ts_resp.data:
            print("No scraped data found in pb_price_events.")
            return
            
        latest_ts = latest_ts_resp.data[0]["created_at"]
        print(f"Latest scrape timestamp: {latest_ts}")
        
        # 2. Fetch all raw price events from pb_price_events matching this timestamp
        print(f"Fetching all raw price events for timestamp {latest_ts}...")
        events_resp = supabase.table("pb_price_events") \
            .select("asin, floor_price, rating, reviews, sales_rank, brand, seller_name, is_buy_box_winner, shipping_price, category_name, created_at, marketplace") \
            .eq("created_at", latest_ts) \
            .execute()
            
        events = events_resp.data
        if not events:
            print("No matching price events found.")
            return
            
        print(f"Retrieved {len(events)} raw items from Apify. Fetching product titles...")
        
        # 3. Fetch product titles from pb_category_competitors to enrich the report
        asins = [e["asin"] for e in events if e.get("asin")]
        titles_map = {}
        if asins:
            titles_resp = supabase.table("pb_category_competitors") \
                .select("asin, title") \
                .in_("asin", asins) \
                .execute()
            titles_map = {t["asin"]: t["title"] for t in (titles_resp.data or [])}
            
        # 4. Compile Markdown report
        print("Compiling raw scraped data report...")
        md_lines = []
        md_lines.append("# SADDL Pricing Intelligence — Raw Scraped Apify Data")
        md_lines.append("")
        md_lines.append(f"This report displays the complete list of **{len(events)} raw products** scraped in your latest Apify search run at **{latest_ts}**.")
        md_lines.append("")
        md_lines.append("| SI. NO | ASIN | Product Title | Category Name | Price | Rating | Reviews | Brand | Seller Name | Buy Box? | Shipping |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        
        for idx, e in enumerate(events, start=1):
            asin = e.get("asin") or "N/A"
            title = titles_map.get(asin) or "N/A (Title not stored in pool)"
            cat_name = e.get("category_name") or "Unknown"
            price = e.get("floor_price")
            rating = e.get("rating")
            reviews = e.get("reviews")
            brand = e.get("brand") or "Generic"
            seller = e.get("seller_name") or "Unknown"
            is_bb = e.get("is_buy_box_winner")
            shipping = e.get("shipping_price")
            
            # Format display strings
            price_str = f"**{price:.2f}**" if price is not None else "N/A"
            rating_str = f"{rating:.1f} ★" if rating is not None else "N/A"
            reviews_str = f"{reviews:,}" if reviews is not None else "0"
            is_bb_str = "✅ Yes" if is_bb else "No"
            shipping_str = f"{shipping:.2f}" if shipping is not None and shipping > 0 else "Free"
            
            # Clean and truncate title
            title_clean = title.replace("|", "\\|").strip()
            if len(title_clean) > 60:
                title_clean = title_clean[:57] + "..."
                
            md_lines.append(
                f"| {idx} | `{asin}` | {title_clean} | {cat_name} | {price_str} | {rating_str} | {reviews_str} | {brand} | {seller} | {is_bb_str} | {shipping_str} |"
            )
            
        md_lines.append("")
        md_lines.append(f"*Report compiled on: {latest_ts} (latest raw Apify scrape run)*")
        
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_scraped_apify_data.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
        print("Report successfully generated!")
        
    except Exception as e:
        err_str = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Error compiling report: {err_str}", file=sys.stderr)

if __name__ == "__main__":
    main()
