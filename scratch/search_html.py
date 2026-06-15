import re

def search_file(path):
    print(f"Searching {path}...")
    for encoding in ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'latin-1']:
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"  Successfully read with {encoding}")
            # Find client_id, currentClientId, acme_store, s2c-uae, etc.
            matches = re.findall(r'currentClientId\s*=\s*[\'"][^\'"]+[\'"]', content)
            print(f"  currentClientId matches: {matches}")
            matches_acme = re.findall(r'acme_store', content)
            print(f"  acme_store count: {len(matches_acme)}")
            
            # Find account select options
            matches_opt = re.findall(r'<option[^>]*>.*?</option>', content, re.IGNORECASE)
            print(f"  Total option tags count: {len(matches_opt)}")
            for opt in matches_opt[:10]:
                print(f"    Option: {opt.strip()}")
            return
        except UnicodeError:
            continue

search_file('dashboard/price_benchmarking.html')
