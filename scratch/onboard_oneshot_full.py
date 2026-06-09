
import requests
import psycopg2
import os
import sys
import json
from dotenv import load_dotenv

# Fix path
sys.path.append(os.getcwd())

load_dotenv()

# Configuration
SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")
API_BASE = "http://127.0.0.1:8000/api/v1/benchmarking"
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "saddl_secret_token_123")
CLIENT_ID = "oneshot_uae"
MARKETPLACE = "UAE"

def onboard_and_analyze():
    if not SADDL_DATABASE_URL:
        print("❌ SADDL_DATABASE_URL not found in .env")
        return

    try:
        # 1. Fetch ASINs from SADDL
        print("🔗 Connecting to SADDL to fetch product list...")
        conn = psycopg2.connect(SADDL_DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT asin 
                FROM sc_raw.bsr_history 
                WHERE marketplace_id IN ('A2VIGQ35RCS4UG', 'A17E79C6D8DWNP')
            """)
            asins = [r[0] for r in cur.fetchall()]
        conn.close()
        
        if not asins:
            print("⚠️ No products found in SADDL for these IDs.")
            return

        print(f"✅ Found {len(asins)} products for {CLIENT_ID}.")

        # 2. Register Client and Listings
        print(f"📦 Registering products in Pricing Analysis project...")
        headers = {"X-Internal-Token": INTERNAL_TOKEN, "Content-Type": "application/json"}
        
        # Create Client with CORRECT FIELDS (from our previous SQL fix)
        client_resp = requests.post(f"{API_BASE}/clients", headers=headers, json={
            "client_id": CLIENT_ID,
            "name": "OneShot UAE",
            "org_id": "oneshot_org",
            "marketplace": MARKETPLACE
        })
        if client_resp.status_code not in (200, 201):
            print(f"❌ Failed to create client: {client_resp.text}")
            return

        # Upsert Listings
        success_count = 0
        first_error = None
        for i, asin in enumerate(asins):
            # FIX: Added ?client_id= to the URL for the security check
            listing_resp = requests.post(f"{API_BASE}/listings?client_id={CLIENT_ID}", headers=headers, json={
                "client_id": CLIENT_ID,
                "marketplace": MARKETPLACE,
                "asin": asin,
                "sku_id": f"oneshot-{asin}",
                "listing_price": 0.0,
                "currency": "AED"
            })
            if listing_resp.status_code in (200, 201):
                success_count += 1
            elif not first_error:
                first_error = f"{listing_resp.status_code}: {listing_resp.text}"
            
            if (i+1) % 50 == 0:
                print(f"  Processed {i+1}/{len(asins)} products...")

        if first_error:
            print(f"⚠️ Warning: Some products failed. First error: {first_error}")

        print(f"✅ Successfully linked {success_count} products to {CLIENT_ID}.")

        # 3. Trigger Apify Market Analysis
        print(f"🚀 Triggering Apify to scrape competitor prices for {success_count} products...")
        resp = requests.post(f"{API_BASE}/trigger-scrape", headers=headers, params={"marketplace": MARKETPLACE}, json=asins)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"\n✨ SUCCESS! Apify analysis triggered.")
            print(f"Dataset ID: {result.get('dataset_id')}")
            print(f"Wait 3-5 minutes, then run fetch_apify_results.py with this ID.")
        else:
            print(f"❌ Failed to trigger scrape: {resp.text}")

    except Exception as e:
        print(f"❌ Error during onboarding: {e}")

if __name__ == "__main__":
    onboard_and_analyze()
