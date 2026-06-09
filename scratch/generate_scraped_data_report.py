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
        
        print("Fetching category names mapping...")
        categories_resp = supabase.table("pb_categories") \
            .select("id, name") \
            .execute()
        
        category_map = {str(c["id"]): c["name"] for c in (categories_resp.data or [])}
        
        print("Fetching recently scraped competitor data...")
        competitors_resp = supabase.table("competitor_products") \
            .select("parent_asin, competitor_asin, competitor_title, competitor_price, reviews, rating, category_id, brand, scraped_at") \
            .order("scraped_at", desc=True) \
            .limit(100) \
            .execute()
            
        competitors = competitors_resp.data
        if not competitors:
            print("No competitor data found in the database.")
            return
            
        print(f"Retrieved {len(competitors)} items. Compiling Markdown report with SI. NO...")
        
        # Build Markdown content
        md_lines = []
        md_lines.append("# SADDL Pricing Intelligence — Scraped Competitors Report")
        md_lines.append("")
        md_lines.append("Here is the list of recently scraped competitor products with ratings and serial numbers.")
        md_lines.append("")
        md_lines.append("| SI. NO | Category Name | Category ID | Product Title | Price (AED/SAR) | Rating | Reviews | Parent ASIN | Competitor ASIN | Brand |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        
        for idx, c in enumerate(competitors, start=1):
            cat_id = str(c.get("category_id") or "")
            cat_name = category_map.get(cat_id) or "Unknown Category"
            title = c.get("competitor_title") or "N/A"
            price = c.get("competitor_price")
            rating = c.get("rating")
            reviews = c.get("reviews")
            parent_asin = c.get("parent_asin") or "N/A"
            comp_asin = c.get("competitor_asin") or "N/A"
            brand = c.get("brand") or "Generic"
            
            # Format price, rating, reviews
            price_str = f"**{price:.2f}**" if price is not None else "N/A"
            rating_str = f"{rating:.1f} ★" if rating is not None else "N/A"
            reviews_str = f"{reviews:,}" if reviews is not None else "0"
            
            # Clean and truncate title for markdown display
            title_clean = title.replace("|", "\\|").strip()
            if len(title_clean) > 80:
                title_clean = title_clean[:77] + "..."
                
            md_lines.append(
                f"| {idx} | {cat_name} | `{cat_id}` | {title_clean} | {price_str} | {rating_str} | {reviews_str} | `{parent_asin}` | `{comp_asin}` | {brand} |"
            )
            
        md_lines.append("")
        md_lines.append(f"*Report compiled on: {competitors[0].get('scraped_at')}*")
        
        # Write to the new filename
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraped_data_with_ratings.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
        print("Report successfully generated!")
        
    except Exception as e:
        err_str = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Error compiling report: {err_str}", file=sys.stderr)

if __name__ == "__main__":
    main()
