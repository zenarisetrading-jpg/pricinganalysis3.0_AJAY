import requests
import json

def main():
    url = "http://127.0.0.1:8000/api/v1/benchmarking/recommendations"
    params = {"client_id": "oneshot_uae"}
    headers = {
        "X-Internal-Token": "saddl_secret_token_123",
        "X-Client-Id": "oneshot_uae"
    }
    
    print("Fetching recommendations from the live local API...")
    try:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            recs = data.get("recommendations", [])
            print("\nAPI Response Current Prices:")
            print(f"{'Parent ASIN':<15} | {'API Current Price':<20}")
            print("-" * 40)
            for r in sorted(recs, key=lambda x: x["asin"]):
                print(f"{r['asin']:<15} | {r['current_price']:<20}")
        else:
            print(f"Failed to fetch: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
