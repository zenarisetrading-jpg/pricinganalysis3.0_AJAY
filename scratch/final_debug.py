import requests
url = 'http://localhost:8000/api/v1/benchmarking/performance'
params = {'client_id': 'oneshot_uae', 'performance_date': '2026-05-09'}
headers = {'X-Internal-Token': 'saddl_secret_token_123', 'X-Client-Id': 'oneshot_uae'}
resp = requests.get(url, params=params, headers=headers)
data = resp.json()
print(f"Debug Date: {data.get('debug_date')}")
print(f"Row count: {len(data.get('rows', []))}")
