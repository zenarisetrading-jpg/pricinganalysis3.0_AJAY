import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import sys
sys.path.append('d:/pricing_analysis')
from main import app

load_dotenv('d:/pricing_analysis/.env')

client = TestClient(app)

response = client.get("/api/v1/benchmarking/overview?client_id=s2c_test")
print("Status Code:", response.status_code)
if response.status_code == 200:
    data = response.json()
    print("parent_asin_count:", data.get("parent_asin_count"))
    print("rows length:", len(data.get("rows", [])))
else:
    print("Error:", response.text)
