import os
import psycopg2
import json
from dotenv import load_dotenv

load_dotenv()

def test_query():
    url = os.getenv("SADDL_DATABASE_URL")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        account_id = "oneshot_uae"
        
        query = """
        WITH parent_mapping AS (
            SELECT 
                b.category_name,
                COALESCE(s.parent_asin, b.asin) as parent_asin,
                b.asin as child_asin,
                b.rank,
                COALESCE(p.title, b.asin) as title
            FROM sc_raw.bsr_history b
            LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
            LEFT JOIN (SELECT DISTINCT ON (asin) asin, title FROM ads.product_catalog) p ON b.asin = p.asin
            WHERE b.account_id = %s
              AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
        ),
        latest_rank_by_parent AS (
            SELECT
                category_name,
                parent_asin,
                MIN(rank) as best_rank,
                MAX(title) as parent_title
            FROM parent_mapping
            GROUP BY category_name, parent_asin
        )
        SELECT 
            l.category_name, 
            COUNT(l.parent_asin) as asin_count,
            AVG(l.best_rank) as avg_rank,
            JSON_AGG(
                JSON_BUILD_OBJECT(
                    'asin', l.parent_asin,
                    'rank', l.best_rank,
                    'title', l.parent_title
                ) ORDER BY l.best_rank ASC
            ) as products
        FROM latest_rank_by_parent l
        GROUP BY l.category_name
        ORDER BY avg_rank ASC;
        """
        
        cur.execute(query, (account_id,))
        rows = cur.fetchall()
        
        total_products = 0
        for r in rows:
            products = r[3]
            total_products += len(products)
            print(f"Category: {r[0]} | Products: {len(products)}")
            for p in products:
                print(f"   - {p['asin']} (Rank: {p['rank']})")
                
        print(f"\nTOTAL UNIQUE PRODUCTS: {total_products}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
