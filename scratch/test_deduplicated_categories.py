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
        
        print("--- Testing Deduplicated Category Query for s2c_test ---")
        query = """
        WITH parent_mapping AS (
            SELECT DISTINCT ON (b.asin)
                b.category_name,
                COALESCE(s.parent_asin, b.asin) as parent_asin,
                b.asin as child_asin,
                b.rank,
                COALESCE(p.title, b.asin) as title
            FROM sc_raw.bsr_history b
            LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
            LEFT JOIN (SELECT DISTINCT ON (asin) asin, title FROM ads.product_catalog) p ON b.asin = p.asin
            WHERE b.account_id = 's2c_test'
              AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
            ORDER BY b.asin
        ),
        primary_category_per_parent AS (
            SELECT DISTINCT ON (parent_asin)
                parent_asin,
                category_name,
                rank as best_rank,
                title
            FROM parent_mapping
            ORDER BY parent_asin, rank ASC
        )
        SELECT 
            l.category_name, 
            COUNT(l.parent_asin) as asin_count,
            AVG(l.best_rank) as avg_rank,
            JSON_AGG(
                JSON_BUILD_OBJECT(
                    'asin', l.parent_asin,
                    'rank', l.best_rank,
                    'title', l.title
                ) ORDER BY l.best_rank ASC
            ) as products
        FROM primary_category_per_parent l
        GROUP BY l.category_name
        ORDER BY avg_rank ASC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        for r in rows:
            print(f"\nCategory: {r[0]} (Count: {r[1]})")
            for p in r[3]:
                print(f"  - ASIN: {p['asin']} | Rank: {p['rank']} | Title: {p['title'][:60]}")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    main()
