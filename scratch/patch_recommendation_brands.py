import sys
import json
sys.path.insert(0, '.')
from db import get_supabase_client

def patch_brands():
    sb = get_supabase_client()
    
    print("Fetching all pending recommendations...")
    res = sb.table('pb_recommendations').select('id, client_id, asin, metadata').eq('status', 'pending').execute()
    recs = res.data or []
    print(f"Found {len(recs)} pending recommendations.")
    
    # 1. Gather all competitor ASINs across all recommendations that need a brand lookup
    comp_asins_to_lookup = set()
    for rec in recs:
        meta = rec.get('metadata') or {}
        competitors = meta.get('competitors') or []
        for c in competitors:
            c_asin = c.get('asin')
            c_brand = c.get('brand')
            if c_asin and (not c_brand or c_brand in ('None', 'null', 'NULL')):
                comp_asins_to_lookup.add(c_asin)
                
    print(f"Identified {len(comp_asins_to_lookup)} unique competitor ASINs that need brand lookup.")
    
    if not comp_asins_to_lookup:
        print("No competitor brands need patching.")
        return

    # 2. Query brand from pb_category_competitors
    brand_map = {}
    comp_asins_list = list(comp_asins_to_lookup)
    
    # Supabase allows in operations, but we should chunk to avoid query length limits if large
    chunk_size = 200
    for i in range(0, len(comp_asins_list), chunk_size):
        chunk = comp_asins_list[i:i+chunk_size]
        p_res = sb.table('pb_category_competitors').select('asin, brand').in_('asin', chunk).execute()
        for r in p_res.data or []:
            asin = r.get('asin')
            brand = r.get('brand')
            if asin and brand and brand not in ('None', 'null', 'NULL'):
                brand_map[asin] = brand

    print(f"Loaded {len(brand_map)} brand mappings from pb_category_competitors.")

    # 3. Query competitor_products for any remaining ASINs
    remaining_asins = [a for a in comp_asins_list if a not in brand_map]
    if remaining_asins:
        for i in range(0, len(remaining_asins), chunk_size):
            chunk = remaining_asins[i:i+chunk_size]
            cp_res = sb.table('competitor_products').select('competitor_asin, brand').in_('competitor_asin', chunk).execute()
            for r in cp_res.data or []:
                asin = r.get('competitor_asin')
                brand = r.get('brand')
                if asin and brand and brand not in ('None', 'null', 'NULL'):
                    brand_map[asin] = brand

        print(f"Loaded brand mappings. Total now: {len(brand_map)}")

    # 4. Patch metadata and update recommendations
    updated_count = 0
    for rec in recs:
        rec_id = rec['id']
        meta = rec.get('metadata') or {}
        competitors = meta.get('competitors') or []
        
        patched = False
        for c in competitors:
            c_asin = c.get('asin')
            c_brand = c.get('brand')
            if c_asin and (not c_brand or c_brand in ('None', 'null', 'NULL')):
                lookup_brand = brand_map.get(c_asin)
                if lookup_brand:
                    c['brand'] = lookup_brand
                    patched = True
                    
        if patched:
            # Update recommendation in Supabase
            sb.table('pb_recommendations').update({'metadata': meta}).eq('id', rec_id).execute()
            updated_count += 1
            
    print(f"Successfully patched {updated_count} recommendations in the database.")

if __name__ == '__main__':
    patch_brands()
