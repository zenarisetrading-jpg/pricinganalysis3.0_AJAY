#!/usr/bin/env python3
"""
Competitor Pricing Scraper and Database Integration.
Queries active Browse Nodes from bsr_history, scrapes the Amazon Best Sellers list
via ScrapeGraphAI v2 API (primary), Crawl4AI local browser (second fallback), and Firecrawl (third fallback).
Stores competitor ranking, prices, and reviews in Supabase.
"""

import os
import sys
import json
import asyncio
import re
import argparse
from datetime import date
import requests
import psycopg2
from psycopg2.extras import execute_values

# Crawl4AI is optional — only used as third fallback if installed
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

# Amazon Marketplace ID to Domain suffix map
MARKETPLACE_DOMAINS = {
    "A2VIGQ35RCS4UG": "ae",      # UAE
    "A17E79C6D8DWNP": "sa",      # Saudi Arabia
    "ATVPDKIKX0DER": "com",      # US
    "A1F83G8C2ARO7P": "co.uk",   # UK
    "A1PA6795UKMFR9": "de",      # Germany
    "A13V1IB3VIYZZH": "fr",      # France
    "APJ6JRA9NG5V4": "it",      # Italy
    "A1RKKUPIHCS9HS": "es",      # Spain
    "A2EUQ1WTGCTBG2": "ca",      # Canada
    "A1VC38T7YXB528": "jp",      # Japan
    "A21TJRUUN4KGV": "in",      # India
    "A39IBJ37TRP1C6": "com.au",  # Australia
    "A1AM78C64UM0Y8": "com.mx",  # Mexico
    "A19N3NI8XO75BD": "sg",      # Singapore
}

DOMAIN_MARKETPLACES = {v: k for k, v in MARKETPLACE_DOMAINS.items()}

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS sc_raw.competitor_pricing (
    id BIGSERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    marketplace_id VARCHAR(20) NOT NULL,
    category_id VARCHAR(255) NOT NULL,
    category_name VARCHAR(255),
    account_id VARCHAR(100) NOT NULL DEFAULT 'unknown',
    rank INTEGER NOT NULL,
    asin VARCHAR(100),
    brand VARCHAR(255),
    title TEXT NOT NULL,
    price VARCHAR(100),
    price_numeric NUMERIC(14,2),
    currency VARCHAR(100),
    rating NUMERIC(3,2),
    reviews_count INTEGER,
    product_url TEXT,
    image_url TEXT,
    pulled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_date, marketplace_id, category_id, asin, account_id)
);

CREATE INDEX IF NOT EXISTS idx_competitor_pricing_lookup
    ON sc_raw.competitor_pricing (report_date, marketplace_id, category_id);

CREATE INDEX IF NOT EXISTS idx_competitor_pricing_asin
    ON sc_raw.competitor_pricing (asin);
"""

ALTER_DDL = """
ALTER TABLE sc_raw.competitor_pricing 
ADD COLUMN IF NOT EXISTS account_id VARCHAR(100) NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS category_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS brand VARCHAR(255);

ALTER TABLE sc_raw.competitor_pricing DROP CONSTRAINT IF EXISTS competitor_pricing_report_date_marketplace_id_category_id_rank_key;
ALTER TABLE sc_raw.competitor_pricing DROP CONSTRAINT IF EXISTS competitor_pricing_report_date_marketplace_id_category_id_a_key;
ALTER TABLE sc_raw.competitor_pricing DROP CONSTRAINT IF EXISTS competitor_pricing_report_date_marketplace_id_category_id_asin_account_key;

ALTER TABLE sc_raw.competitor_pricing 
ADD CONSTRAINT competitor_pricing_report_date_marketplace_id_category_id_asin_account_key 
UNIQUE (report_date, marketplace_id, category_id, asin, account_id);
"""

def load_env():
    """Manually parse .env file to load variables."""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Amazon Competitor Pricing from Best Sellers using ScrapeGraphAI."
    )
    parser.add_argument(
        "-n", "--node",
        type=str,
        help="Amazon category browse node ID for manual testing."
    )
    parser.add_argument(
        "-d", "--domain",
        type=str,
        default="ae",
        help="Amazon domain extension (e.g. ae, sa, com) for manual testing."
    )
    parser.add_argument(
        "-a", "--account",
        type=str,
        default="unknown",
        help="Client account ID (e.g. oneshot_uae) for manual testing."
    )
    parser.add_argument(
        "-t", "--target-count",
        type=int,
        default=30,
        help="Target number of unique competitor products to extract (e.g. 30 or 50). Controls pagination."
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Write scraped results to the Supabase database."
    )
    parser.add_argument(
        "--key",
        type=str,
        help="ScrapeGraphAI API key override."
    )
    parser.add_argument(
        "--firecrawl-key",
        type=str,
        help="Firecrawl API key override."
    )
    return parser.parse_args()

def ensure_schema(db_url, fallback_db_url=None):
    """Ensure the competitor_pricing table exists and is up to date in the database."""
    print("[*] Checking competitor_pricing database table schema...")
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(TABLE_DDL)
                cur.execute(ALTER_DDL)
            conn.commit()
        print("[+] Table schema verified/created successfully.")
        return db_url
    except Exception as e:
        print(f"[-] Warning: Failed to connect to database host: {e}")
        if fallback_db_url:
            print("[*] Retrying connection using fallback database URL...")
            try:
                with psycopg2.connect(fallback_db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(TABLE_DDL)
                        cur.execute(ALTER_DDL)
                    conn.commit()
                print("[+] Table schema verified/created successfully using fallback host.")
                return fallback_db_url
            except Exception as fe:
                print(f"[!] Error creating schema on fallback DB: {fe}")
                sys.exit(1)
        else:
            sys.exit(1)

def get_active_categories(db_url):
    """Query unique marketplace, category ID, name, and account ID from active BSR history."""
    sql = """
        SELECT DISTINCT marketplace_id, category_id, category_name, account_id
        FROM sc_raw.bsr_history
        WHERE report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
          AND category_id IS NOT NULL;
    """
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
    except Exception as e:
        print(f"[!] Error fetching active categories from DB: {e}")
        return []

def extract_asin(url):
    """Attempt to extract the 10-character Amazon ASIN from the product URL."""
    if not url:
        return None
    parts = url.split('/')
    for i, part in enumerate(parts):
        if part in ('dp', 'product') and i + 1 < len(parts):
            asin = parts[i + 1].split('?')[0]
            if len(asin) == 10:
                return asin
    return None

def infer_missing_brands(products, anthropic_key):
    """Batch infers missing brand names from product titles using Anthropic if available."""
    if not anthropic_key:
        return products
        
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[-] Warning: 'anthropic' package not installed. Skipping LLM brand inference.")
        return products

    missing_products = [p for p in products if not p.get("brand") and p.get("title")]
    if not missing_products:
        return products

    print(f"[*] Inferring missing brands for {len(missing_products)} products via Anthropic...")
    try:
        client = Anthropic(api_key=anthropic_key)
        batch_size = 50
        for i in range(0, len(missing_products), batch_size):
            batch = missing_products[i:i+batch_size]
            prompt = "Extract the brand name from each of the following product titles. Return a JSON object mapping the ID to the brand string. If there is no clear brand, return 'Generic'. Output ONLY valid JSON without markdown wrapping.\n\n"
            for idx, p in enumerate(batch):
                prompt += f"ID: {idx} | Title: {p['title']}\n"
            
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.content[0].text
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                content = match.group(0)
                
            result_dict = json.loads(content)
            for idx, p in enumerate(batch):
                brand = result_dict.get(str(idx)) or result_dict.get(idx)
                if brand:
                    p["brand"] = brand
    except Exception as e:
        print(f"[-] Error during LLM brand inference: {e}")

    return products

def scrape_category(url, api_key, domain):
    """Call ScrapeGraphAI extract API and return list of products."""
    schema = {
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "brand": {"type": "string"},
                        "title": {"type": "string"},
                        "price": {"type": "string"},
                        "price_numeric": {"type": "number"},
                        "currency": {"type": "string"},
                        "rating": {"type": "number"},
                        "reviews_count": {"type": "integer"},
                        "url": {"type": "string"},
                        "asin": {"type": "string"},
                        "image_url": {"type": "string"}
                    },
                    "required": ["rank", "title"]
                }
            }
        },
        "required": ["products"]
    }

    payload = {
        "url": url,
        "prompt": (
            "Extract the complete list of all best sellers products displayed on the page. "
            "Make sure to extract every product listed (typically up to 50 items per page). "
            "For each product, extract its rank, brand name (infer from title if necessary), product title/name, price (raw text), "
            "price_numeric (float number), currency, rating (decimal), "
            "reviews_count (integer), detailed URL, and image URL."
        ),
        "schema": schema
    }

    headers = {
        "SGAI-APIKEY": api_key,
        "Content-Type": "application/json"
    }

    api_url = "https://v2-api.scrapegraphai.com/api/extract"
    response = requests.post(api_url, json=payload, headers=headers, timeout=180)
    response.raise_for_status()
    res_data = response.json()

    if "json" in res_data:
        json_data = res_data["json"]
    elif "result" in res_data:
        json_data = res_data["result"]
    else:
        raise ValueError(f"ScrapeGraphAI response missing json/result: {res_data}")

    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    products = []
    if isinstance(json_data, dict):
        products = json_data.get("products", [])
    elif isinstance(json_data, list):
        products = json_data

    # Clean and format URLs
    for p in products:
        p_url = p.get("url", "")
        if p_url and p_url.startswith("/"):
            p["url"] = f"https://www.amazon.{domain}{p_url}"
        if not p.get("asin") and p.get("url"):
            p["asin"] = extract_asin(p["url"])

    return products

def scrape_category_firecrawl(url, api_key, domain):
    """Call Firecrawl scrape API to extract competitor products."""
    schema = {
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "brand": {"type": "string"},
                        "title": {"type": "string"},
                        "price": {"type": "string"},
                        "price_numeric": {"type": "number"},
                        "currency": {"type": "string"},
                        "rating": {"type": "number"},
                        "reviews_count": {"type": "integer"},
                        "url": {"type": "string"},
                        "asin": {"type": "string"},
                        "image_url": {"type": "string"}
                    },
                    "required": ["rank", "title"]
                }
            }
        },
        "required": ["products"]
    }

    payload = {
        "url": url,
        "formats": ["json"],
        "jsonOptions": {
            "schema": schema,
            "prompt": (
                "Extract the complete list of all best sellers products displayed on the page. "
                "Make sure to extract every product listed (typically up to 50 items per page). "
                "For each product, extract its rank, brand name (infer from title if necessary), product title/name, price (raw text), "
                "price_numeric (float number), currency, rating (decimal), "
                "reviews_count (integer), detailed URL, and image URL."
            )
        }
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    api_url = "https://api.firecrawl.dev/v1/scrape"
    response = requests.post(api_url, json=payload, headers=headers, timeout=180)
    response.raise_for_status()
    res_data = response.json()

    if not res_data.get("success"):
        raise ValueError(f"Firecrawl scrape failed: {res_data.get('error')}")

    data = res_data.get("data", {})
    json_data = data.get("json", {})

    products = []
    if isinstance(json_data, dict):
        products = json_data.get("products", [])
    elif isinstance(json_data, list):
        products = json_data

    # Clean and format URLs
    for p in products:
        p_url = p.get("url", "")
        if p_url and p_url.startswith("/"):
            p["url"] = f"https://www.amazon.{domain}{p_url}"
        if not p.get("asin") and p.get("url"):
            p["asin"] = extract_asin(p["url"])

    return products

# CSS schema for Crawl4AI (rank inferred from position order)
_CRAWL4AI_CSS_SCHEMA = {
    "name": "Amazon Bestsellers",
    "baseSelector": "div.zg-grid-general-faceout",
    "fields": [
        {"name": "title",       "selector": "a span",            "type": "text"},
        {"name": "price",       "selector": "span.p13n-sc-price, .a-color-price", "type": "text"},
        {"name": "rating",      "selector": "span.a-icon-alt",   "type": "text"},
        {"name": "reviews",     "selector": "span.a-size-small", "type": "text"},
        {"name": "product_url", "selector": "a.a-link-normal",   "type": "attribute", "attribute": "href"},
        {"name": "image_url",   "selector": "img",               "type": "attribute", "attribute": "src"},
    ]
}

def scrape_category_crawl4ai(url, domain):
    """Use local Crawl4AI (headless Chromium) to scrape Amazon Best Sellers.
    Runs the async crawler synchronously via a new event loop.
    Rank is inferred from position order (Amazon displays items in rank order).
    """
    if not CRAWL4AI_AVAILABLE:
        raise ImportError("crawl4ai is not installed. Run: pip3 install crawl4ai==0.4.247")

    async def _scrape():
        strategy = JsonCssExtractionStrategy(_CRAWL4AI_CSS_SCHEMA, verbose=False)
        async with AsyncWebCrawler(
            verbose=False,
            headless=True,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ) as crawler:
            result = await crawler.arun(
                url=url,
                extraction_strategy=strategy,
                bypass_cache=True,
                delay_before_return_html=3.0,
            )
            if not result.success or not result.extracted_content:
                return []
            raw = json.loads(result.extracted_content)
            return raw

    # Run in a new event loop (safe from sync context)
    loop = asyncio.new_event_loop()
    try:
        raw_products = loop.run_until_complete(_scrape())
    finally:
        loop.close()

    # Normalize: rank from position, parse price/rating
    products = []
    for i, p in enumerate(raw_products):
        title = str(p.get("title", "")).strip()
        if not title:
            continue

        price_text = str(p.get("price", "")).strip()
        price_numeric = None
        currency = None
        if price_text:
            nums = re.findall(r'[\d,.]+', price_text)
            if nums:
                try:
                    price_numeric = float(nums[0].replace(',', ''))
                except ValueError:
                    pass
            currency = "AED" if "AED" in price_text else ("USD" if "$" in price_text else None)

        rating_text = str(p.get("rating", ""))
        rating = None
        m = re.search(r'([\d.]+)', rating_text)
        if m:
            try:
                rating = float(m.group(1))
            except ValueError:
                pass

        reviews_text = str(p.get("reviews", "")).replace(',', '')
        reviews_count = None
        try:
            reviews_count = int(re.sub(r'[^\d]', '', reviews_text)) if reviews_text else None
        except ValueError:
            pass

        p_url = str(p.get("product_url", "")).strip()
        if p_url and p_url.startswith("/"):
            p_url = f"https://www.amazon.{domain}{p_url}"

        asin = extract_asin(p_url)
        
        products.append({
            "rank": i + 1,  # Amazon displays items in rank order
            "brand": p.get("brand"),
            "title": title,
            "price": price_text,
            "price_numeric": price_numeric,
            "currency": currency,
            "rating": rating,
            "reviews_count": reviews_count,
            "url": p_url,
            "asin": asin,
            "image_url": str(p.get("image_url", "")).strip()
        })

    return products


def scrape_category_with_limit(base_url, sgai_key, fc_key, domain, target_count=30):
    """
    Scrapes the best sellers category, paginating to page 2 if needed.
    Tries ScrapeGraphAI first, then Crawl4AI (free local browser), then Firecrawl as last resort.
    """
    # 1. Scrape Page 1
    products = []
    scraped_via = None
    
    if sgai_key:
        try:
            print(f"[*] Scraping Page 1 via ScrapeGraphAI: {base_url}")
            products = scrape_category(base_url, sgai_key, domain)
            scraped_via = "ScrapeGraphAI"
        except Exception as e:
            print(f"[-] Warning: ScrapeGraphAI failed on Page 1: {e}")

    if not products and CRAWL4AI_AVAILABLE:
        try:
            print(f"[*] Fallback: Scraping Page 1 via Crawl4AI (local browser): {base_url}")
            products = scrape_category_crawl4ai(base_url, domain)
            scraped_via = "Crawl4AI"
        except Exception as e:
            print(f"[-] Warning: Crawl4AI also failed on Page 1: {e}")

    if not products and fc_key:
        try:
            print(f"[*] Fallback: Scraping Page 1 via Firecrawl: {base_url}")
            products = scrape_category_firecrawl(base_url, fc_key, domain)
            scraped_via = "Firecrawl"
        except Exception as e:
            print(f"[!] Error: Firecrawl also failed on Page 1: {e}")

    if not products:
        raise ValueError("No products could be extracted from Page 1 by any scraper (SGAI / Crawl4AI / Firecrawl).")

    print(f"[+] Page 1 ({scraped_via}): Extracted {len(products)} products.")

    # Deduplicate in-memory by ASIN
    seen_asins = set()
    unique_products = []
    for p in products:
        asin = p.get("asin")
        if asin and asin not in seen_asins:
            seen_asins.add(asin)
            unique_products.append(p)
        elif not asin:
            unique_products.append(p)

    # 2. Check if we need Page 2
    if len(seen_asins) < target_count:
        print(f"[*] Got {len(seen_asins)} unique products with ASINs, which is less than target {target_count}.")
        sep = "&" if "?" in base_url else "?"
        page_2_url = f"{base_url}{sep}pg=2"
        
        page_2_products = []
        page_2_scraped_via = None
        
        # Try to use the same scraper that succeeded on Page 1 first,
        # but always prefer free options (Crawl4AI) before paid APIs (Firecrawl).
        scraping_methods = []
        if scraped_via == "ScrapeGraphAI":
            scraping_methods = [
                ("ScrapeGraphAI", lambda: scrape_category(page_2_url, sgai_key, domain)),
                ("Crawl4AI", lambda: scrape_category_crawl4ai(page_2_url, domain)),
                ("Firecrawl", lambda: scrape_category_firecrawl(page_2_url, fc_key, domain)),
            ]
        elif scraped_via == "Crawl4AI":
            scraping_methods = [
                ("Crawl4AI", lambda: scrape_category_crawl4ai(page_2_url, domain)),
                ("ScrapeGraphAI", lambda: scrape_category(page_2_url, sgai_key, domain)),
                ("Firecrawl", lambda: scrape_category_firecrawl(page_2_url, fc_key, domain)),
            ]
        else:  # scraped_via == "Firecrawl" or unknown
            scraping_methods = [
                ("Firecrawl", lambda: scrape_category_firecrawl(page_2_url, fc_key, domain)),
                ("Crawl4AI", lambda: scrape_category_crawl4ai(page_2_url, domain)),
                ("ScrapeGraphAI", lambda: scrape_category(page_2_url, sgai_key, domain)),
            ]
            
        for name, method in scraping_methods:
            try:
                print(f"[*] Scraping Page 2 via {name}: {page_2_url}")
                page_2_products = method()
                page_2_scraped_via = name
                break
            except Exception as e:
                print(f"[-] Warning: {name} failed on Page 2: {e}")
                
        if page_2_products:
            print(f"[+] Page 2 ({page_2_scraped_via}): Extracted {len(page_2_products)} products.")
            added_count = 0
            for p in page_2_products:
                asin = p.get("asin")
                if asin and asin not in seen_asins:
                    seen_asins.add(asin)
                    unique_products.append(p)
                    added_count += 1
                elif not asin:
                    unique_products.append(p)
            print(f"[+] Added {added_count} new unique products from Page 2. Total unique products: {len(unique_products)}")
        else:
            print("[-] Warning: Failed to extract Page 2 with any scraper.")

    return unique_products

def upsert_competitors(db_url, report_date, marketplace_id, category_id, products, account_id, category_name):
    """Upsert parsed competitor products into sc_raw.competitor_pricing."""
    if not products:
        return 0

    # Deduplicate products by ASIN in the batch to avoid duplicates in ON CONFLICT insertion
    seen_asins = set()
    deduped_products = []
    for p in products:
        asin = p.get("asin")
        if not asin:
            continue
        if asin not in seen_asins:
            seen_asins.add(asin)
            deduped_products.append(p)

    if not deduped_products:
        print("[-] No valid products with ASINs to upsert.")
        return 0

    values = [
        (
            report_date,
            marketplace_id,
            category_id,
            category_name,
            account_id,
            p["rank"],
            p["asin"],
            p.get("brand"),
            p["title"],
            p.get("price"),
            p.get("price_numeric"),
            p.get("currency"),
            p.get("rating"),
            p.get("reviews_count"),
            p.get("url"),
            p.get("image_url")
        )
        for p in deduped_products
    ]

    sql = """
        INSERT INTO sc_raw.competitor_pricing (
            report_date, marketplace_id, category_id, category_name, account_id, rank, asin, brand, title,
            price, price_numeric, currency, rating, reviews_count, product_url, image_url
        ) VALUES %s
        ON CONFLICT (report_date, marketplace_id, category_id, asin, account_id)
        DO UPDATE SET
            rank = EXCLUDED.rank,
            category_name = COALESCE(EXCLUDED.category_name, competitor_pricing.category_name),
            brand = COALESCE(EXCLUDED.brand, competitor_pricing.brand),
            title = EXCLUDED.title,
            price = EXCLUDED.price,
            price_numeric = EXCLUDED.price_numeric,
            currency = EXCLUDED.currency,
            rating = EXCLUDED.rating,
            reviews_count = EXCLUDED.reviews_count,
            product_url = EXCLUDED.product_url,
            image_url = EXCLUDED.image_url,
            pulled_at = NOW();
    """

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, values)
        conn.commit()
    return len(deduped_products)

def main():
    load_env()
    args = parse_args()

    # Determine API key and DB url
    sgai_key = args.key or os.environ.get("SGAI_API_KEY")
    fc_key = args.firecrawl_key or os.environ.get("FIRECRAWL_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not sgai_key and not fc_key:
        print("[!] Error: No API keys found. Please provide at least SGAI_API_KEY or FIRECRAWL_API_KEY in env or command line.")
        sys.exit(1)

    db_url_direct = os.environ.get("DATABASE_URL_DIRECT")
    db_url_pooler = os.environ.get("DATABASE_URL")
    db_url_pricing = os.environ.get("PRICING_DATABASE_URL")
    
    db_url = db_url_direct or db_url_pooler or db_url_pricing
    fallback_db_url = db_url_pooler if db_url_direct else None
    
    if not db_url:
        print("[!] Error: Database URL not found in env or .env file.")
        sys.exit(1)

    # 1. Run migrations if table doesn't exist
    db_url = ensure_schema(db_url, fallback_db_url)

    today = date.today().strftime("%Y-%m-%d")

    # 2. Determine target categories to scrape
    categories_to_scrape = []  # List of tuples: (marketplace_id, category_id, domain, category_name, account_id)

    if args.node:
        # Manual execution mode
        domain = args.domain.lower()
        marketplace_id = DOMAIN_MARKETPLACES.get(domain, f"UNKNOWN_{domain.upper()}")
        print(f"[*] Manual Mode: Scrape node {args.node} on domain {domain} (Marketplace: {marketplace_id}, Account: {args.account})")
        categories_to_scrape.append((marketplace_id, args.node, domain, None, args.account))
    else:
        # Automated pipeline mode
        print("[*] Pipeline Mode: Fetching active categories from bsr_history...")
        active_cats = get_active_categories(db_url)
        print(f"[+] Found {len(active_cats)} active categories in catalog history.")
        
        # Query categories already scraped today to avoid duplicate scrapes and save credits
        scraped_today = set()
        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT category_id 
                        FROM sc_raw.competitor_pricing 
                        WHERE report_date = %s;
                    """, (today,))
                    scraped_today = {r[0] for r in cur.fetchall()}
            print(f"[+] Found {len(scraped_today)} categories already scraped today. Skipping them to save credits.")
        except Exception as e:
            print(f"[-] Warning: Failed to query already scraped categories: {e}")

        for m_id, cat_id, cat_name, acc_id in active_cats:
            if cat_id in scraped_today:
                continue
            domain = MARKETPLACE_DOMAINS.get(m_id)
            if not domain:
                print(f"[-] Warning: Unsupported marketplace ID {m_id}. Skipping.")
                continue
            categories_to_scrape.append((m_id, cat_id, domain, cat_name, acc_id))

    # 3. Perform scraping and insertion
    for m_id, cat_id, domain, cat_name, acc_id in categories_to_scrape:
        target_url = f"https://www.amazon.{domain}/gp/bestsellers/goods/{cat_id}"
        print(f"\n[*] Scraping {target_url} (Account: {acc_id}, Category Name: {cat_name})...")

        try:
            # We want to ensure we get at least target_count results (default 30)
            products = scrape_category_with_limit(target_url, sgai_key, fc_key, domain, target_count=args.target_count)
            print(f"[+] Extracted {len(products)} competitor products.")
            
            # Print manually for validation
            for p in products[:3]:
                print(f"    - Rank {p['rank']}: {p['title'][:50]}... (Price: {p.get('price')}, Rating: {p.get('rating')})")

            # Run post-processing to infer missing brands using Anthropic
            products = infer_missing_brands(products, anthropic_key)

            # Write to CSV instead of database for testing
            import csv
            products_to_save = products[:30]
            if products_to_save:
                csv_filename = f"competitors_{cat_id}_{today}.csv"
                # Collect all unique keys from the products
                keys = set()
                for p in products_to_save:
                    keys.update(p.keys())
                keys = list(keys)
                
                with open(csv_filename, 'w', newline='', encoding='utf-8') as output_file:
                    dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(products_to_save)
                print(f"[+] Saved {len(products_to_save)} products to {csv_filename}")
            else:
                print("[-] No products to save.")
        except Exception as e:
            print(f"[!] Error processing category {cat_id} ({domain}): {e}")

if __name__ == "__main__":
    main()
