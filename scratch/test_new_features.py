
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# We'll use the local server if it's running, otherwise we just test the logic via internal calls if possible.
# But here we'll assume the server is running on localhost:8000
BASE_URL = "http://localhost:8000/api/v1/benchmarking"
TOKEN = os.getenv("INTERNAL_TOKEN", "test-token")
HEADERS = {"X-Internal-Token": TOKEN}

def test_automation_toggle():
    print("Testing Automation Toggle...")
    # 1. Disable automation
    resp = requests.post(f"{BASE_URL}/toggle-automation?enabled=false", headers=HEADERS)
    print(f"Toggle OFF: {resp.status_code} - {resp.json()}")
    
    # 2. Verify status
    resp = requests.get(f"{BASE_URL}/automation-status")
    print(f"Status: {resp.json()}")
    
    # 3. Try trigger scrape (should be skipped)
    resp = requests.post(f"{BASE_URL}/trigger-scrape?marketplace=UAE", headers=HEADERS)
    print(f"Trigger Scrape (expect skipped): {resp.json()}")
    
    # 4. Re-enable automation
    resp = requests.post(f"{BASE_URL}/toggle-automation?enabled=true", headers=HEADERS)
    print(f"Toggle ON: {resp.status_code} - {resp.json()}")

def test_upload_data():
    print("\nTesting Data Upload...")
    records = [
        {
            "asin": "B07P7MZG97",
            "marketplace": "UAE",
            "floor_price": 45.99,
            "buy_box_price": 45.99,
            "seller_name": "Test Seller",
            "is_buy_box_winner": True
        }
    ]
    resp = requests.post(f"{BASE_URL}/upload-data", headers=HEADERS, json={"records": records})
    print(f"Upload Response: {resp.status_code} - {resp.json()}")

if __name__ == "__main__":
    # Note: This requires the FastAPI server to be running!
    # If the server is not running, these tests will fail.
    try:
        test_automation_toggle()
        test_upload_data()
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Make sure to run 'uvicorn main:app --reload' first.")
