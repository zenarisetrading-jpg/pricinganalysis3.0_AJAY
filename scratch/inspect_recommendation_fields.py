import requests
import json

def main():
    url = "http://127.0.0.1:8000/api/v1/benchmarking/recommendations"
    params = {"client_id": "oneshot_uae"}
    headers = {
        "X-Internal-Token": "saddl_secret_token_123",
        "X-Client-Id": "oneshot_uae"
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            recs = data.get("recommendations", [])
            if recs:
                print("Sample Recommendation Fields:")
                first = recs[0]
                print(json.dumps(first, indent=2))
            else:
                print("No recommendations found.")
        else:
            print(f"Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
