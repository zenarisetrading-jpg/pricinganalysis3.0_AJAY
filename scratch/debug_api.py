import requests
import json

try:
    resp = requests.get("http://localhost:8000/api/v1/benchmarking/performance?client_id=s2c-uae")
    print(f"Status: {resp.status_code}")
    print(f"Body: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
