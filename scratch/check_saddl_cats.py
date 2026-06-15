import sys
sys.path.insert(0, '.')
from features.price_benchmarking.saddl_db import execute_saddl_query

cat_id1 = '12373019031'
cat_id2 = '12373047031'

res1 = execute_saddl_query("SELECT COUNT(DISTINCT asin) FROM sc_raw.bsr_history WHERE category_id = %s", (cat_id1,))
print(f'SADDL Category {cat_id1} unique asins: {res1[0][0]}')

res2 = execute_saddl_query("SELECT COUNT(DISTINCT asin) FROM sc_raw.bsr_history WHERE category_id = %s", (cat_id2,))
print(f'SADDL Category {cat_id2} unique asins: {res2[0][0]}')

res_both = execute_saddl_query("SELECT COUNT(DISTINCT asin) FROM sc_raw.bsr_history WHERE category_id IN (%s, %s)", (cat_id1, cat_id2))
print(f'SADDL Both unique asins: {res_both[0][0]}')
