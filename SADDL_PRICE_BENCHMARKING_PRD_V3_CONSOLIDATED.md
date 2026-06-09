# SADDL Price Benchmarking Module — PRD v3 (Apify Migration)
## Complete Implementation Specification

**Version:** 3.0 — Apify-native architecture. Supersedes PRD v2 entirely.
**Stack:** FastAPI · Supabase (Postgres) · Railway · Apify (scraping) · SP-API (price updates only)
**Target Markets:** Amazon UAE (amazon.ae) and Amazon KSA (amazon.sa)

---

## 0. What Changed from v2 → v3

### The Core Pivot: Keepa Removal

PRD v2 used a hybrid model where Keepa handled competitor discovery and SP-API handled live pricing. **This is now completely removed.** Apify replaces both.

| Function | PRD v2 Source | PRD v3 Source | Why Changed |
|---|---|---|---|
| Competitor Discovery | Keepa Product Finder | Apify Actor | Keepa unreliable for UAE/KSA markets |
| Live Market Prices | SP-API `getCompetitiveSummary` | Apify Actor | SP-API doesn't return Buy Box winner or seller details |
| Price Change Events | SP-API `ANY_OFFER_CHANGED` | Apify webhook | Apify provides richer data (seller name, shipping) |
| Your Listing Price | SP-API listings table | SP-API listings table | ✅ Unchanged |
| Price Updates | SP-API | SP-API | ✅ Unchanged |

### Files That Must Be Changed

| File | Action | Reason |
|---|---|---|
| `keepa_client.py` | **DELETE** | No longer needed |
| `sp_pricing_client.py` | **DELETE** | Replaced by `apify_client.py` |
| `routes.py` | **MODIFY** | Remove Keepa endpoints, add Apify webhook |
| Schema SQL | **MODIFY** | Add seller_name, is_buy_box_winner, shipping_price |
| `__init__.py` | **MODIFY** | Remove Keepa imports, add Apify |

### New Files to Create

- `apify_client.py` — Apify SDK wrapper
- Migration SQL — Schema changes only (don't drop tables)

---

## 1. Mental Model (Unchanged from v2)

### 1.1 Business Context

SADDL serves two types of users:
- **Own brands** (S2C/Zenarise) — Aslam's own Amazon accounts, used for dogfooding
- **Agency clients** — boutique Amazon PPC agencies who manage multiple seller accounts

Each Amazon seller account operating in one marketplace is one **Client**. Clients are grouped under **Organizations** (the agency or seller group that owns them).

### 1.2 Hierarchy

```
Organization  →  one agency or seller group
  └── Client  →  one Amazon seller account × one marketplace
        └── SKU →  one ASIN listed by that client
```

Real examples:
```
Org: s2c
  ├── Client: s2c-uae      (Amazon UAE account)
  └── Client: s2c-ksa      (Amazon KSA account)

Org: bubble-bros
  └── Client: bubble-bros-uae

Org: oneshot
  └── Client: oneshot-uae
```

### 1.3 Competitor Data Model (Unchanged)

Competitors are NOT stored per-client. They are stored per **category + marketplace** as a shared pool. Each client's effective competitor set = shared pool minus their personal exclusions.

This means if Bubble Bros and One Shot both compete in UAE electrolyte drinkware, the competitor ASIN pool is stored once and both clients query from it independently. No duplication.

### 1.4 Data Source Strategy (UPDATED FOR APIFY)

| Job | Source | Notes |
|---|---|---|
| Competitor ASIN discovery | **Apify Actor** | Scrapes Best Sellers or category pages |
| Current market prices (live) | **Apify Actor** | Scrapes PDPs for price, Buy Box, seller details |
| Real-time price change events | **Apify webhook** | Pushed to FastAPI when scrape completes |
| Your own listing price | SP-API listings table | Already in Supabase, unchanged |
| Velocity, ACoS, sessions | SP-API performance table | Already in Supabase, unchanged |
| Price history | Built from `pb_price_events` | No third party needed |

### 1.5 Storage Tiers (Unchanged)

```
TIER 1 — pb_price_events
  Raw price events per ASIN (now from Apify instead of SP-API)
  90-day TTL. Nightly purge job deletes rows older than 90 days.
  NOT client-specific. Market data belongs to everyone.

TIER 2 — pb_price_snapshots_daily
  One aggregated row per (asin, marketplace, date)
  floor / ceiling / median / mean computed from Tier 1 events
  Permanent. Never deleted. Grows at ~1 row per ASIN per day.
  NOT client-specific.

TIER 3 — pb_client_snapshots_daily
  One row per (client_id, sku_id, date)
  your_price / percentile_rank / zone / index_vs_median
  Permanent. Client-specific position in the market.
```

---

## 2. Schema Changes — Migration SQL

**DO NOT drop existing tables.** Run this migration to add new fields:

```sql
-- =============================================================================
-- PRICE BENCHMARKING MODULE — SCHEMA MIGRATION v2 → v3
-- Run this in Supabase SQL Editor to add Apify-specific fields
-- =============================================================================

-- Add Apify-specific fields to Tier 1 events table
ALTER TABLE pb_price_events 
    ADD COLUMN IF NOT EXISTS seller_name TEXT,
    ADD COLUMN IF NOT EXISTS is_buy_box_winner BOOLEAN,
    ADD COLUMN IF NOT EXISTS shipping_price NUMERIC(10,2);

-- Update categories table to remove Keepa dependency
-- (keepa_cat_id can stay for backward compatibility, but won't be used)
ALTER TABLE pb_categories 
    ADD COLUMN IF NOT EXISTS apify_search_query TEXT,
    ADD COLUMN IF NOT EXISTS apify_category_url TEXT;

-- Add index for faster webhook lookups
CREATE INDEX IF NOT EXISTS idx_price_events_asin_marketplace 
    ON pb_price_events(asin, marketplace, recorded_at DESC);

-- Update competitor source field to allow 'apify'
ALTER TABLE pb_category_competitors 
    DROP CONSTRAINT IF EXISTS pb_category_competitors_source_check;

ALTER TABLE pb_category_competitors 
    ADD CONSTRAINT pb_category_competitors_source_check 
    CHECK (source IN ('keepa_bsr', 'apify_bsr', 'apify_search', 'manual_admin'));
```

**All other schema from PRD v2 remains unchanged.** The 12 core tables stay as-is.

---

## 3. Apify Setup Instructions

### 3.1 Get Your Apify API Token

1. **Log in to Apify Console:** https://console.apify.com/
2. **Navigate to Settings** (click your profile icon in top-right → Settings)
3. **Click "Integrations" in left sidebar**
4. **Find "Personal API tokens" section**
5. **Click "Add new token"**
   - Name it: `SADDL_Production`
   - Leave scopes as default (full access)
   - Click "Create"
6. **Copy the token** — it looks like: `apify_api_ABCxyz123...`
7. **Add to Railway environment variables:**
   ```
   APIFY_TOKEN=apify_api_ABCxyz123...
   ```

⚠️ **CRITICAL:** Never commit this token to git. Railway only.

### 3.2 Choose the Right Actors

Apify has dozens of Amazon scrapers. Here are the two you need:

#### Actor 1: Competitor Discovery (One-time / Weekly)

**Purpose:** Find new ASINs in a category to seed `pb_category_competitors`

**Recommended Actor:** `junglee/amazon-crawler`
- **Why:** Supports UAE/KSA, handles category pages, residential proxies
- **Actor ID:** `junglee/amazon-crawler`
- **Actor URL:** https://console.apify.com/actors/junglee~amazon-crawler

**Alternative (if junglee is down):** `clockworks/amazon-product-scraper`

#### Actor 2: Live Pricing (Once Daily - 24 hours)

**Purpose:** Scrape specific ASINs for current price, Buy Box, seller

**Recommended Actor:** `junglee/amazon-crawler` (same as above)
- **Why:** Can handle both category scraping AND product page scraping
- **Input type:** Pass array of ASINs instead of category URL

**Alternative:** `clockworks/amazon-product-scraper`

### 3.3 Test the Actor in Apify Console

Before writing code, verify the actor works for UAE/KSA:

1. **Open the actor:** https://console.apify.com/actors/junglee~amazon-crawler
2. **Click "Try it"**
3. **Configure the input:**

```json
{
  "asins": ["B0B1234ABC"],
  "domain": "amazon.ae",
  "proxyConfiguration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"],
    "apifyProxyCountry": "AE"
  },
  "maxItems": 10,
  "waitMs": 3000
}
```

4. **Click "Start"**
5. **Wait 30-60 seconds**
6. **Click "Results" tab**
7. **Verify the output contains:**
   - `asin`
   - `price` (number)
   - `sellerName` (text)
   - `isBuyBoxWinner` (boolean)
   - `url` (should be amazon.ae or amazon.sa)

If you see this data, the actor is working. Copy the exact field names for the code.

### 3.4 Set Up the Webhook

Apify can push data to your FastAPI server when a scrape completes.

1. **In Apify Console, go to Actor → Settings → Webhooks**
2. **Click "Add webhook"**
3. **Configure:**
   - **Event:** `Actor run succeeded`
   - **Request URL:** `https://YOUR_RAILWAY_DOMAIN.up.railway.app/api/v1/benchmarking/webhook/apify`
   - **Payload template:** Leave as default (JSON)
4. **Click "Save"**

Now every successful scrape will POST to your FastAPI route.

### 3.5 Proxy Configuration (Critical for UAE/KSA)

Amazon detects and blocks datacenter IPs aggressively, especially in Gulf markets.

**You MUST use Residential proxies.** Here's the config:

```json
{
  "proxyConfiguration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"],
    "apifyProxyCountry": "AE"  // or "SA" for KSA
  }
}
```

**Why this matters:**
- Datacenter proxies = instant CAPTCHA or 503 errors
- Residential proxies = appear as real UAE/KSA users
- `apifyProxyCountry` ensures correct currency and Buy Box visibility

**Cost:** Residential proxies cost ~$12.50 per GB. Scraping 100 ASINs = ~50MB. Budget $50-100/month for pricing data.

---

## 4. Implementation Files

### 4.1 `apify_client.py` (NEW)

This replaces both `keepa_client.py` and `sp_pricing_client.py`.

```python
"""
Apify client for Amazon scraping in UAE/KSA markets.
Handles competitor discovery and live pricing via Apify actors.
"""

import os
from typing import List, Dict, Optional
from apify_client import ApifyClient

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN environment variable not set")

client = ApifyClient(APIFY_TOKEN)

# Actor ID for Amazon scraping
AMAZON_ACTOR_ID = "junglee/amazon-crawler"


def trigger_price_scrape(asins: List[str], marketplace: str) -> str:
    """
    Triggers an Apify actor to scrape specific ASINs in UAE/KSA.
    
    Args:
        asins: List of ASINs to scrape
        marketplace: "UAE" or "KSA"
        
    Returns:
        dataset_id: ID of the Apify dataset containing results
    """
    country_code = "AE" if marketplace == "UAE" else "SA"
    domain = "amazon.ae" if marketplace == "UAE" else "amazon.sa"
    
    run_input = {
        "asins": asins,
        "domain": domain,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
            "apifyProxyCountry": country_code
        },
        "maxItems": len(asins),
        "waitMs": 3000  # Wait 3s between requests to avoid rate limits
    }
    
    # Trigger the actor (returns immediately, scraping happens async)
    run = client.actor(AMAZON_ACTOR_ID).call(run_input=run_input)
    
    return run["defaultDatasetId"]


def trigger_category_discovery(category_url: str, marketplace: str, max_items: int = 100) -> str:
    """
    Scrapes a category page (e.g., Best Sellers) to find new competitor ASINs.
    
    Args:
        category_url: Full Amazon category URL (e.g., https://amazon.ae/Best-Sellers-Kitchen/zgbs/kitchen)
        marketplace: "UAE" or "KSA"
        max_items: Number of products to scrape (default 100)
        
    Returns:
        dataset_id: ID of the Apify dataset containing results
    """
    country_code = "AE" if marketplace == "UAE" else "SA"
    
    run_input = {
        "startUrls": [{"url": category_url}],
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
            "apifyProxyCountry": country_code
        },
        "maxItems": max_items,
        "waitMs": 3000
    }
    
    run = client.actor(AMAZON_ACTOR_ID).call(run_input=run_input)
    
    return run["defaultDatasetId"]


def fetch_dataset_results(dataset_id: str) -> List[Dict]:
    """
    Fetches results from a completed Apify dataset.
    
    Args:
        dataset_id: The dataset ID returned from trigger_* functions
        
    Returns:
        List of scraped items (each item is a dict with asin, price, etc.)
    """
    dataset = client.dataset(dataset_id)
    items = dataset.list_items().items
    
    return items


def parse_apify_item(item: Dict, marketplace: str) -> Dict:
    """
    Parses a raw Apify result item into our standardized format.
    
    Args:
        item: Raw item from Apify dataset
        marketplace: "UAE" or "KSA"
        
    Returns:
        Parsed dict ready for pb_price_events insertion
    """
    # Handle price parsing (Apify returns various formats)
    raw_price = item.get("price") or item.get("currentPrice") or item.get("listPrice")
    
    # Extract numeric price from string like "AED 45.99" or "45.99"
    floor_price = None
    if raw_price:
        if isinstance(raw_price, (int, float)):
            floor_price = float(raw_price)
        elif isinstance(raw_price, str):
            # Remove currency symbols and parse
            import re
            price_match = re.search(r'[\d,]+\.?\d*', raw_price.replace(',', ''))
            if price_match:
                floor_price = float(price_match.group())
    
    return {
        "asin": item.get("asin"),
        "marketplace": marketplace,
        "floor_price": floor_price,
        "buy_box_price": floor_price if item.get("isBuyBoxWinner") else None,
        "seller_name": item.get("sellerName"),
        "is_buy_box_winner": item.get("isBuyBoxWinner", False),
        "shipping_price": item.get("shippingPrice"),
        "event_type": "poll",
        "recorded_at": "NOW()"  # Postgres function
    }
```

### 4.2 `routes.py` Changes

**REMOVE these routes:**
```python
# DELETE THESE — Keepa is gone
POST /categories/{id}/refresh-competitors  # Used Keepa Product Finder
```

**ADD this webhook route:**

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from supabase import Client
from .apify_client import fetch_dataset_results, parse_apify_item
from .benchmarking import calculate_benchmark_scores

router = APIRouter()


@router.post("/webhook/apify")
async def handle_apify_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receives webhook from Apify when a scrape job completes.
    Parses the data and stores it in pb_price_events (Tier 1).
    """
    # Extract dataset ID from webhook payload
    resource = payload.get("resource", {})
    dataset_id = resource.get("defaultDatasetId")
    
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Missing dataset ID in webhook payload")
    
    # Fetch results from Apify dataset
    items = fetch_dataset_results(dataset_id)
    
    if not items:
        return {"status": "success", "processed": 0, "message": "Empty dataset"}
    
    # Determine marketplace from first item's URL
    first_url = items[0].get("url", "")
    marketplace = "UAE" if ".ae" in first_url else "KSA"
    
    # Parse and prepare for bulk insert
    event_rows = []
    for item in items:
        parsed = parse_apify_item(item, marketplace)
        if parsed["asin"] and parsed["floor_price"]:  # Only insert valid data
            event_rows.append(parsed)
    
    # Bulk insert into Tier 1
    if event_rows:
        supabase.table("pb_price_events").insert(event_rows).execute()
    
    # Trigger benchmark calculation in background
    # (Don't block the webhook response)
    background_tasks.add_task(calculate_benchmarks_for_marketplace, marketplace, supabase)
    
    return {
        "status": "success",
        "processed": len(event_rows),
        "marketplace": marketplace,
        "dataset_id": dataset_id
    }


@router.post("/trigger-scrape")
async def trigger_scrape(
    marketplace: str,
    asins: Optional[List[str]] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Manually trigger an Apify scrape for specific ASINs or all tracked competitors.
    
    Args:
        marketplace: "UAE" or "KSA"
        asins: Optional list of ASINs. If None, scrapes all active competitors.
    """
    from .apify_client import trigger_price_scrape
    
    # If no ASINs provided, get all active competitors for this marketplace
    if not asins:
        competitors_resp = supabase.table("pb_category_competitors")\
            .select("asin")\
            .eq("marketplace", marketplace)\
            .eq("is_active", True)\
            .execute()
        
        asins = [r["asin"] for r in (competitors_resp.data or [])]
    
    if not asins:
        raise HTTPException(status_code=404, detail=f"No ASINs found for {marketplace}")
    
    # Trigger the scrape (returns dataset ID)
    dataset_id = trigger_price_scrape(asins, marketplace)
    
    return {
        "status": "scrape_triggered",
        "marketplace": marketplace,
        "asin_count": len(asins),
        "dataset_id": dataset_id,
        "message": "Results will be POSTed to /webhook/apify when ready"
    }


@router.post("/discover-competitors")
async def discover_competitors(
    category_url: str,
    marketplace: str,
    category_id: int,
    max_items: int = 100,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Scrapes a category page to find new competitor ASINs.
    Seeds pb_category_competitors table.
    
    Args:
        category_url: Full Amazon category URL (e.g., Best Sellers page)
        marketplace: "UAE" or "KSA"
        category_id: FK to pb_categories
        max_items: Number of products to scrape
    """
    from .apify_client import trigger_category_discovery, fetch_dataset_results, parse_apify_item
    
    # Trigger the scrape
    dataset_id = trigger_category_discovery(category_url, marketplace, max_items)
    
    # Wait for results (or make this async and use webhook)
    # For simplicity, we'll wait here (blocks for ~30-60s)
    import time
    time.sleep(60)  # Wait for scrape to complete
    
    items = fetch_dataset_results(dataset_id)
    
    # Insert into pb_category_competitors
    competitor_rows = []
    for item in items:
        competitor_rows.append({
            "category_id": category_id,
            "marketplace": marketplace,
            "asin": item.get("asin"),
            "title": item.get("title"),
            "brand": item.get("brand"),
            "source": "apify_bsr",
            "is_active": True,
            "last_bsr_rank": item.get("bsrRank"),
            "added_at": "NOW()",
            "updated_at": "NOW()"
        })
    
    if competitor_rows:
        # Upsert (insert if new, update if exists)
        supabase.table("pb_category_competitors").upsert(
            competitor_rows,
            on_conflict="category_id,asin"
        ).execute()
    
    return {
        "status": "success",
        "competitors_added": len(competitor_rows),
        "category_id": category_id,
        "marketplace": marketplace
    }


def calculate_benchmarks_for_marketplace(marketplace: str, supabase: Client):
    """
    Background task: Calculate benchmarks for all clients in a marketplace.
    Called after webhook inserts new price data.
    """
    # Get all clients in this marketplace
    clients_resp = supabase.table("pb_clients")\
        .select("client_id")\
        .eq("marketplace", marketplace)\
        .eq("is_active", True)\
        .execute()
    
    for client in (clients_resp.data or []):
        # Run benchmark calculation (reuse existing logic from benchmarking.py)
        calculate_benchmark_scores(client["client_id"], supabase)
```

### 4.3 Update `__init__.py`

```python
# Remove these imports (files deleted):
# from .keepa_client import ...
# from .sp_pricing_client import ...

# Add this:
from .apify_client import (
    trigger_price_scrape,
    trigger_category_discovery,
    fetch_dataset_results,
    parse_apify_item
)

__all__ = [
    "trigger_price_scrape",
    "trigger_category_discovery",
    "fetch_dataset_results",
    "parse_apify_item",
    # ... other existing exports
]
```

### 4.4 Files Unchanged

These files from PRD v2 remain exactly as-is:

- `benchmarking.py` — scoring logic is data-source agnostic
- `alerts.py` — alert logic is data-source agnostic
- `nightly.py` — aggregation logic works with any Tier 1 data source

---

## 5. Railway Cron Jobs (UPDATED)

### Job 1: Pricing Scrape (once daily)

**OLD (v2):** Called SP-API directly
**NEW (v3):** Trigger Apify scrape

```bash
Schedule:  0 2 * * *    # 2 AM UAE time daily (10 PM UTC)
Command:   curl -X POST https://YOUR_DOMAIN/api/v1/benchmarking/trigger-scrape \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer $INTERNAL_TOKEN" \
             -d '{"marketplace": "UAE"}'
```

### Job 2: Nightly Aggregation (unchanged)

```bash
Schedule:  0 22 * * *
Command:   curl -X POST https://YOUR_DOMAIN/api/v1/benchmarking/nightly \
             -H "Authorization: Bearer $INTERNAL_TOKEN"
```

---

## 6. Workflow Summary (v3)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Railway Cron triggers /trigger-scrape once daily (2 AM) │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 2. FastAPI calls apify_client.trigger_price_scrape()       │
│    → Sends ASIN list to Apify Actor                         │
│    → Apify uses UAE Residential Proxies                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 3. Apify scrapes amazon.ae PDPs for 30-60 seconds          │
│    → Extracts: price, Buy Box, seller name, shipping        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 4. Apify webhook POSTs to /webhook/apify with results      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 5. FastAPI parses data, inserts into pb_price_events       │
│    (Tier 1 — raw events with 90-day TTL)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 6. Background task calculates benchmarks                    │
│    → Queries your price from SP-API listings table          │
│    → Compares against competitor prices                     │
│    → Writes to pb_client_snapshots_daily (Tier 3)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│ 7. If price too high: generate recommendation               │
│    → Store in pb_recommendations table                      │
│    → Optionally auto-apply via SP-API                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Testing Checklist

After implementation, verify in order:

- [ ] **Schema migration:** Run migration SQL, verify new columns exist in `pb_price_events`
- [ ] **Apify token:** Confirm `APIFY_TOKEN` is set in Railway env vars
- [ ] **Actor test:** Run test scrape in Apify Console for 1 UAE ASIN, verify output has `asin`, `price`, `sellerName`, `isBuyBoxWinner`
- [ ] **Webhook test:** Use Postman to POST mock Apify payload to `/webhook/apify`, verify rows inserted into `pb_price_events`
- [ ] **Manual trigger:** `POST /trigger-scrape` with `marketplace=UAE` and `asins=["B0B1234ABC"]`, verify Apify job starts
- [ ] **Category discovery:** `POST /discover-competitors` with Best Sellers URL, verify ASINs inserted into `pb_category_competitors` with `source=apify_bsr`
- [ ] **End-to-end:** Trigger scrape → wait 60s → check webhook was called → verify `pb_price_events` has new rows → verify `pb_client_snapshots_daily` updated
- [ ] **Cron test:** Manually run Railway cron command, verify it triggers scrape
- [ ] **Error handling:** Send invalid dataset_id to webhook, verify 400 response
- [ ] **Proxy verification:** Check Apify run logs, confirm residential proxies used (log shows country code)

---

## 8. Migration Checklist (v2 → v3)

Execute in this order:

1. **Backup Supabase database** (Supabase Dashboard → Database → Backups → Create backup)
2. **Run schema migration SQL** (Section 2 above)
3. **Add `APIFY_TOKEN` to Railway** (Section 3.1)
4. **Delete files:**
   - `keepa_client.py`
   - `sp_pricing_client.py`
5. **Create file:** `apify_client.py` (Section 4.1)
6. **Update file:** `routes.py` (Section 4.2)
7. **Update file:** `__init__.py` (Section 4.3)
8. **Test Apify actor** in Console (Section 3.3)
9. **Set up Apify webhook** (Section 3.4)
10. **Update Railway cron jobs** (Section 5)
11. **Run testing checklist** (Section 7)

---

## 9. Cost Estimates

### Apify Costs (Pay-as-you-go)

- **Residential proxies:** $12.50 per GB
- **Compute:** ~$0.25 per hour (minimal — scraping is fast)

**Example calculation for 100 ASINs once daily (24-hour frequency):**
- Data transfer: ~50 MB per scrape = 0.05 GB
- 1 scrape/day × 30 days = 30 scrapes/month
- 30 × 0.05 GB = 1.5 GB/month
- **Cost:** 1.5 GB × $12.50 = **~$19/month**

**Scaling:**
- 500 ASINs = ~$95/month
- 1,000 ASINs = ~$190/month

**Optimization tip:** Start with 24-hour frequency for prototype ($19/month for 100 ASINs). Scale to 12-hour ($38/month) or 6-hour ($75/month) when you have paying clients and need faster market reaction times.

### What You're Replacing

- Keepa Product Finder: $19-99/month (unreliable for UAE/KSA)
- SP-API rate limit headaches: priceless

**Prototype Strategy:** At 24-hour frequency with 100 competitor ASINs, you're spending ~$19/month — same as the cheapest Keepa tier but with better UAE/KSA data. Once you have paying clients, you can dial up frequency to 12h ($38/mo) or 6h ($75/mo) for faster price reactions. For bootstrapping S2C dogfooding, daily is perfect.

---

## 10. Apify Actor Field Mapping Reference

When parsing Apify results, these are the field names you'll encounter:

| Apify Field | Our Field | Type | Notes |
|---|---|---|---|
| `asin` | `asin` | string | Always present |
| `price` | `floor_price` | float | May be string like "AED 45.99" — parse it |
| `currentPrice` | `floor_price` | float | Alternative field name |
| `sellerName` | `seller_name` | string | Who has the Buy Box |
| `isBuyBoxWinner` | `is_buy_box_winner` | boolean | True if this seller won |
| `shippingPrice` | `shipping_price` | float | May be null if free shipping |
| `url` | N/A | string | Use to determine marketplace (.ae vs .sa) |
| `title` | N/A | string | For competitor discovery only |
| `brand` | N/A | string | For competitor discovery only |
| `bsrRank` | `last_bsr_rank` | int | Best Sellers Rank |

---

## 11. Troubleshooting Guide

### Problem: Apify scrape fails with 503 errors

**Cause:** Not using residential proxies, or wrong country code
**Fix:** Verify `proxyConfiguration` has `apifyProxyGroups: ["RESIDENTIAL"]` and correct `apifyProxyCountry`

### Problem: Webhook never called

**Cause:** Webhook URL wrong, or actor run failed
**Fix:** Check Apify Console → Actor Runs → click the run → check status. If "Failed", check logs. Verify webhook URL ends with `/webhook/apify`

### Problem: Price parsing fails

**Cause:** Apify returns price as "AED 45.99" string, not float
**Fix:** Use the `parse_apify_item()` function which handles regex parsing

### Problem: No data inserted to `pb_price_events`

**Cause:** `parsed["asin"]` or `parsed["floor_price"]` is None
**Fix:** Add logging to webhook route to see what Apify returned. Some products may have hidden prices.

### Problem: Too expensive — high monthly bill

**Cause:** Scraping too many ASINs or too frequently
**Fix:** For prototype, use 24-hour frequency (~$19/month for 100 ASINs). Only increase to 12h or 6h when you have revenue. Limit competitor pool to top 50-100 ASINs per category.

---

## 12. What NOT to Change

These parts of the system remain untouched in the v2 → v3 migration:

- ✅ Organization/Client hierarchy
- ✅ 3-tier storage (events → market daily → client daily)
- ✅ Competitor pool + client overrides model
- ✅ Benchmarking scoring logic
- ✅ Alert generation rules
- ✅ Recommendation engine
- ✅ SP-API for reading your own prices
- ✅ SP-API for pushing price updates
- ✅ Nightly aggregation job
- ✅ 90-day TTL for Tier 1

**Only the data ingestion layer changed.** Everything downstream is source-agnostic.

---

## Appendix A: Example Apify Payload (Webhook)

When Apify POSTs to your webhook, the payload looks like this:

```json
{
  "userId": "abc123",
  "createdAt": "2026-04-30T10:30:00.000Z",
  "eventType": "ACTOR.RUN.SUCCEEDED",
  "eventData": {
    "actorId": "junglee~amazon-crawler",
    "actorRunId": "xyz789"
  },
  "resource": {
    "id": "xyz789",
    "actId": "junglee~amazon-crawler",
    "status": "SUCCEEDED",
    "defaultDatasetId": "dataset123abc",
    "defaultKeyValueStoreId": "kvstore456def"
  }
}
```

You extract `resource.defaultDatasetId` and pass it to `fetch_dataset_results()`.

---

## Appendix B: Example Apify Dataset Item

When you call `fetch_dataset_results(dataset_id)`, each item looks like:

```json
{
  "asin": "B0B1234ABC",
  "title": "HydroFit Water Bottle 1L",
  "brand": "HydroFit",
  "price": 45.99,
  "currency": "AED",
  "sellerName": "LittleZen Store",
  "isBuyBoxWinner": true,
  "shippingPrice": 0,
  "url": "https://www.amazon.ae/dp/B0B1234ABC",
  "bsrRank": 142,
  "category": "Kitchen & Dining",
  "imageUrl": "https://m.media-amazon.com/images/I/...",
  "reviewCount": 87,
  "rating": 4.6
}
```

You parse this into `pb_price_events` format using `parse_apify_item()`.

---

## Appendix C: Railway Environment Variables

Complete list of required env vars:

```bash
# Existing (from SADDL core)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=ey...
INTERNAL_TOKEN=your-secret-token-for-cron

# New for Price Benchmarking v3
APIFY_TOKEN=apify_api_ABCxyz123...
```

---

**END OF PRD v3**

Next steps:
1. Review this entire document
2. Confirm Apify account access
3. Test actor in Apify Console (Section 3.3)
4. Run schema migration (Section 2)
5. Implement files in order: `apify_client.py` → `routes.py` → `__init__.py`
6. Set up webhook (Section 3.4)
7. Deploy to Railway
8. Run testing checklist (Section 7)
