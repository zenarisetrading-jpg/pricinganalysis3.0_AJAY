import requests
import json

def verify_api():
    headers = {
        'X-Internal-Token': 'benchmarking-secret-2026',
        'X-Client-Id': 'admin'
    }
    url = 'http://127.0.0.1:8000/api/v1/benchmarking/recommendations?client_id=oneshot_uae'
    
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        
        recommendations = data.get('recommendations', [])
        asins = [rec['asin'] for rec in recommendations]
        
        print(f"Total Recommendations: {len(recommendations)}")
        print(f"Unique ASINs: {sorted(list(set(asins)))}")
        
        # Check if any child ASINs are present
        child_asins = ['B0FM469PMF', 'B0CZLNKY2Q', 'B0FFB2F46C', 'B0F6NHKSQ1', 'B0D39R47CC', 'B0CZLK598D', 'B0CZLKLJX5', 'B0FMYLRD2X']
        found_children = [a for a in asins if a in child_asins]
        print(f"Child ASINs found: {len(found_children)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_api()
