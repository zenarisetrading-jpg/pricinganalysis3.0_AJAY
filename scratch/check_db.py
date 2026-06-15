import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('d:/pricing_analysis/.env')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

try:
    res = supabase.table('pb_my_products').select('parent_asin, category, client_id, category_name').execute()
    data = res.data
    
    s2c_test = [r for r in data if r['client_id'] == 's2c_test']
    s2c_uae = [r for r in data if r['client_id'] == 's2c-uae']
    
    print('s2c_test total:', len(s2c_test), 'null category:', len([r for r in s2c_test if not r.get('category') and not r.get('category_name')]))
    print('s2c-uae total:', len(s2c_uae), 'null category:', len([r for r in s2c_uae if not r.get('category') and not r.get('category_name')]))
    
    for r in data:
        if not r.get('category') and not r.get('category_name'):
            print(f"Missing category for ASIN: {r['parent_asin']} client: {r['client_id']}")
            
            # Let's see if we can guess the category from other products or just set it to something default?
            # Actually, the user says "make all the parent_asin which belongs to their category".
            # We need to find the correct category for these ASINs.

except Exception as e:
    print('Error pb_my_products:', e)

try:
    res = supabase.table('pb_product_master').select('*').execute()
    print('pb_product_master count:', len(res.data))
    for r in res.data:
        if r.get('client_id') in ['s2c_test', 's2c-uae']:
            if not r.get('category') and not r.get('category_name'):
                 print(f"pb_product_master missing category for ASIN: {r.get('parent_asin') or r.get('asin')} client: {r['client_id']}")
except Exception as e:
    print('Error pb_product_master:', e)
