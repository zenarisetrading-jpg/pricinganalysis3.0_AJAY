import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:8000/api/v1/benchmarking/accounts"
TOKEN = os.getenv("INTERNAL_TOKEN")

headers = {
    "X-Internal-Token": TOKEN
}

try:
    resp = requests.get(API_URL, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
