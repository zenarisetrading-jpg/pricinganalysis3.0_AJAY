import requests
url = 'http://localhost:8000/api/v1/benchmarking/performance?client_id=oneshot_uae'
headers = {'X-Internal-Token': 'saddl_secret_token_123'}
resp = requests.get(url, headers=headers)
data = resp.json()['rows']
dates = sorted(list(set(r['performance_date'] for r in data)), reverse=True)
print(f"Total rows: {len(data)}")
print(f"Latest 5 dates: {dates[:5]}")
