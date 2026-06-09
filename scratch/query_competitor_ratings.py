import os
import sys

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_supabase_client

def main():
    try:
        # Reconfigure stdout to use utf-8 to avoid encoding crashes on Windows terminal
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

        supabase = get_supabase_client()
        # Query competitor_products table
        response = supabase.table("competitor_products") \
            .select("parent_asin, competitor_asin, competitor_title, brand, rating, reviews, marketplace") \
            .order("parent_asin") \
            .execute()
        
        data = response.data
        if not data:
            print("No competitor data found in 'competitor_products' table.")
            return
        
        print(f"--- Competitor Ratings Summary ({len(data)} items) ---")
        
        current_parent = None
        for row in data:
            parent = row.get("parent_asin")
            if parent != current_parent:
                print(f"\nParent ASIN: {parent}")
                print("-" * 80)
                current_parent = parent
                
            comp_asin = row.get("competitor_asin")
            title = row.get("competitor_title") or "N/A"
            brand = row.get("brand") or "N/A"
            rating = row.get("rating")
            reviews = row.get("reviews")
            
            # Format rating and reviews
            rating_str = f"{rating:.1f} ★" if rating is not None else "N/A (No Rating)"
            reviews_str = f"{reviews:,}" if reviews is not None else "N/A"
            
            # Clean title for display - remove non-ascii chars to be safe if console doesn't support utf-8
            title_clean = title.encode('ascii', 'ignore').decode('ascii')
            short_title = title_clean[:45] + "..." if len(title_clean) > 45 else title_clean
            
            print(f"  - Competitor: {comp_asin:<10} | Brand: {brand:<15} | Rating: {rating_str:<12} | Reviews: {reviews_str:<8} | Title: {short_title}")
            
    except Exception as e:
        print(f"Error querying competitor ratings: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
