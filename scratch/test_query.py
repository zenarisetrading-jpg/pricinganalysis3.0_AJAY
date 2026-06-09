from features.price_benchmarking.saddl_db import execute_saddl_query

query = """
WITH ProductBase AS (
    SELECT DISTINCT ON (b.asin)
        COALESCE(s.parent_asin, b.asin) as parent_asin,
        b.asin as child_asin,
        b.category_name,
        COALESCE(p.title, f.product_name, b.asin) as product_name
    FROM sc_raw.bsr_history b
    LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
    LEFT JOIN (SELECT DISTINCT ON (asin) asin, title FROM ads.product_catalog) p ON b.asin = p.asin
    LEFT JOIN (SELECT DISTINCT ON (asin) asin, product_name FROM sc_raw.fba_inventory WHERE client_id = 'oneshot_uae') f ON b.asin = f.asin
    WHERE b.account_id = 'oneshot_uae'
      AND b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history WHERE account_id = 'oneshot_uae')
),
PriceSales AS (
    SELECT 
        child_asin, 
        ROUND((SUM(ordered_revenue) / NULLIF(SUM(units_ordered), 0))::numeric, 2) as avg_selling_price
    FROM sc_raw.sales_traffic
    WHERE account_id = 'oneshot_uae' AND units_ordered > 0
    GROUP BY child_asin
),
PriceInventory AS (
    SELECT DISTINCT ON (asin) 
        asin, 
        your_price as catalog_price
    FROM sc_raw.fba_inventory
    WHERE client_id = 'oneshot_uae'
    ORDER BY asin, snapshot_date DESC
)
SELECT 
    pb.parent_asin,
    pb.child_asin,
    pb.category_name,
    pb.product_name,
    COALESCE(ps.avg_selling_price, pi.catalog_price, 0.00) as current_price
FROM ProductBase pb
LEFT JOIN PriceSales ps ON pb.child_asin = ps.child_asin
LEFT JOIN PriceInventory pi ON pb.child_asin = pi.asin
ORDER BY pb.parent_asin, pb.category_name, pb.child_asin;
"""

res = execute_saddl_query(query)
for r in res[:5]:
    print(r)
