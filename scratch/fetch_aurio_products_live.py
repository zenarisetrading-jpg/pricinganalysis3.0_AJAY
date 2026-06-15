import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("SADDL_DATABASE_URL")
    if not db_url:
        print("SADDL_DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Query to select products for aurio_uae with category_name, category_id, child_asin, parent_asin, and calculated price
        query = """
        WITH RecentBSR AS (
            -- Get the most recent report_date BSR records for aurio_uae
            SELECT DISTINCT ON (asin)
                asin,
                category_name,
                category_id,
                marketplace_id
            FROM sc_raw.bsr_history
            WHERE account_id = 'aurio_uae'
              AND report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history WHERE account_id = 'aurio_uae')
        ),
        ParentMapping AS (
            -- Get parent_asin from sales_traffic
            SELECT DISTINCT child_asin, parent_asin
            FROM sc_raw.sales_traffic
            WHERE account_id = 'aurio_uae'
        ),
        AvgSellingPrice AS (
            -- Calculate average selling price from sales traffic
            SELECT child_asin, 
                   ROUND((SUM(ordered_revenue) / NULLIF(SUM(units_ordered), 0))::numeric, 2) as avg_price
            FROM sc_raw.sales_traffic
            WHERE account_id = 'aurio_uae' AND units_ordered > 0
            GROUP BY child_asin
        ),
        CatalogPrice AS (
            -- Fallback to latest catalog price from FBA inventory
            SELECT DISTINCT ON (asin) asin, your_price
            FROM sc_raw.fba_inventory
            WHERE client_id = 'aurio_uae'
              AND your_price IS NOT NULL AND your_price > 0
            ORDER BY asin, snapshot_date DESC
        )
        SELECT 
            b.category_name,
            b.category_id,
            b.asin as child_asin,
            COALESCE(m.parent_asin, b.asin) as parent_asin,
            COALESCE(s.avg_price, c.your_price, 0.00) as current_price
        FROM RecentBSR b
        LEFT JOIN ParentMapping m ON b.asin = m.child_asin
        LEFT JOIN AvgSellingPrice s ON b.asin = s.child_asin
        LEFT JOIN CatalogPrice c ON b.asin = c.asin
        ORDER BY b.category_name, parent_asin, child_asin;
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print(f"\nFound {len(rows)} products for aurio_uae:")
        print(f"{'Category Name':<30} | {'Category ID':<15} | {'ASIN':<15} | {'Parent ASIN':<15} | {'Price (AED)':<10}")
        print("-" * 95)
        for r in rows[:15]:  # show first 15 rows
            print(f"{str(r[0])[:30]:<30} | {str(r[1]):<15} | {str(r[2]):<15} | {str(r[3]):<15} | {str(r[4]):<10}")
        
        if len(rows) > 15:
            print(f"... and {len(rows) - 15} more products.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
