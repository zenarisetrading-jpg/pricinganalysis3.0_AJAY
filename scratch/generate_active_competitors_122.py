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
        
        target_parent_asin = "B0FWKLG3JJ"
        
        print(f"Fetching category names mapping...")
        categories_resp = supabase.table("pb_categories") \
            .select("id, name") \
            .execute()
        category_map = {str(c["id"]): c["name"] for c in (categories_resp.data or [])}
        
        print(f"Fetching active competitors for parent ASIN {target_parent_asin}...")
        competitors_resp = supabase.table("competitor_products") \
            .select("parent_asin, competitor_asin, competitor_title, competitor_price, reviews, rating, category_id, brand, scraped_at, marketplace") \
            .eq("parent_asin", target_parent_asin) \
            .order("competitor_price", desc=False) \
            .execute()
            
        competitors = competitors_resp.data
        if not competitors:
            print(f"No competitor data found for {target_parent_asin} in database.")
            return
            
        print(f"Retrieved {len(competitors)} active competitors. Compiling Markdown report...")
        
        # Build Markdown content
        md_lines = []
        md_lines.append(f"# SADDL Pricing Intelligence — Active Competitors for `{target_parent_asin}`")
        md_lines.append("")
        md_lines.append(f"This report lists all **{len(competitors)} active competitor products** currently mapped to your parent ASIN **`{target_parent_asin}`** in your dashboard UI, ordered by price (lowest to highest).")
        md_lines.append("")
        md_lines.append("| SI. NO | ASIN | Product Title | Category Name | Price | Rating | Reviews | Brand | Marketplace | Scraped At |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        
        for idx, c in enumerate(competitors, start=1):
            comp_asin = c.get("competitor_asin") or "N/A"
            title = c.get("competitor_title") or "N/A"
            cat_id = str(c.get("category_id") or "")
            cat_name = category_map.get(cat_id) or "Unknown Category"
            price = c.get("competitor_price")
            rating = c.get("rating")
            reviews = c.get("reviews")
            brand = c.get("brand") or "Generic"
            marketplace = c.get("marketplace") or "KSA"
            scraped_at = c.get("scraped_at") or "N/A"
            
            # Format display strings
            currency = "SAR" if marketplace == "KSA" else "AED"
            price_str = f"**{price:.2f} {currency}**" if price is not None else "N/A"
            rating_str = f"{rating:.1f} ★" if rating is not None else "N/A"
            reviews_str = f"{reviews:,}" if reviews is not None else "0"
            
            # Clean and truncate title
            title_clean = title.replace("|", "\\|").strip()
            if len(title_clean) > 65:
                title_clean = title_clean[:62] + "..."
                
            md_lines.append(
                f"| {idx} | `{comp_asin}` | {title_clean} | {cat_name} | {price_str} | {rating_str} | {reviews_str} | {brand} | {marketplace} | {scraped_at[:19]} |"
            )
            
        md_lines.append("")
        md_lines.append(f"*Report compiled on: {competitors[0].get('scraped_at')}*")
        
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "active_competitors_122.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
        print("Report successfully generated!")
        
    except Exception as e:
        err_str = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Error compiling report: {err_str}", file=sys.stderr)

if __name__ == "__main__":
    main()
