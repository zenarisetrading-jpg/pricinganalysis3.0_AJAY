from features.price_benchmarking.saddl_db import execute_saddl_query
query = """
WITH LatestSales AS (
    SELECT DISTINCT ON (child_asin)
        child_asin as asin,
        report_date,
        ordered_revenue,
        units_ordered,
        CASE 
            WHEN units_ordered > 0 THEN ROUND(ordered_revenue / units_ordered, 2)
            ELSE 0 
        END as calculated_price
    FROM sc_raw.sales_traffic
    WHERE child_asin IN (
        'B0FNN5WKDG', 'B0DGLGPN1N', 'B0DLX3GJNJ', 'B0DLX3Y8JN', 
        'B0DLX4FKPT', 'B0DLXPQZCJ', 'B0FM43BSB2', 'B0FM45GBTY'
    )
    ORDER BY child_asin, report_date DESC
)
SELECT asin, calculated_price FROM LatestSales;
"""
res = execute_saddl_query(query)
for r in res:
    print(f'ASIN: {r[0]} | Query Price: {r[1]}')
