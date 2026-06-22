# Amazon Best Sellers Competitor Scraper

This repository contains the automated pipeline for extracting daily ranking, pricing, and review metrics from Amazon Best Sellers categories worldwide. It automatically populates a Supabase database with clean, structured competitor data.

## Architecture & Fallback Logic

To ensure 100% data completeness despite Amazon's bot protections, this script implements a **3-Tier Fallback System**:

1. **Tier 1: ScrapeGraphAI (Primary)**  
   - **How it works:** A paid cloud API that uses LLMs to natively extract structured data from Amazon URLs.
   - **Pros:** Handles dynamic CSS, reads actual rank badges, standardizes price logic seamlessly.
2. **Tier 2: Crawl4AI (Local Browser Fallback)**
   - **How it works:** An open-source, local headless Chromium browser script running asynchronously. Extracts data via CSS selectors.
   - **Pros:** Completely free.
   - **Cons:** Bypasses Amazon rank badges by inferring rank based on position in the grid.
3. **Tier 3: Firecrawl (Last Resort)**
   - **How it works:** A cloud scraping API focused on text rendering and LLM extraction.

### Brand Inference (Post-Processing)
Since Amazon titles are often messy, the script features an automated **OpenAI Brand Inference** post-processing layer. If any scraper fails to extract a distinct brand name natively (e.g. Crawl4AI), the script batches the product titles and passes them to `gpt-4o-mini` to extract the correct brand name before insertion into the database.

---

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- A PostgreSQL database (e.g., Supabase)

### 2. Installation
Install the dependencies using pip:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Ensure you have the following populated:
- `DATABASE_URL_DIRECT`
- `DATABASE_URL`
- `SGAI_API_KEY` (ScrapeGraphAI)
- `OPENAI_API_KEY` (For brand inference)
- `FIRECRAWL_API_KEY` (Optional)

---

## Usage

### Automated Pipeline Mode
When run without arguments, the script will connect to your database, read the active `category_id` list from `sc_raw.bsr_history`, and scrape all active categories, skipping any that have already been pulled today.

```bash
python3 scrape_competitors.py --write-db
```

### Manual Testing Mode
You can scrape a specific Amazon Browse Node manually to test selectors or API keys without saving to the DB.

```bash
python3 scrape_competitors.py -n "22247225031" -d "ae" -a "aurio_uae" -t 30
```
- `-n`: The Amazon Category Browse Node
- `-d`: The domain suffix (e.g., `ae`, `com`, `co.uk`)
- `-a`: Your internal account ID/identifier
- `-t`: Target product count (e.g., `30` or `50`). The script will paginate to Page 2 if needed.
- `--write-db`: Append this flag to explicitly save manual runs to the database.

## Database Schema
The script automatically handles migrations. On its first run, it ensures the following schema exists:
- `sc_raw.competitor_pricing` table with columns for `report_date`, `marketplace_id`, `category_id`, `rank`, `asin`, `brand`, `title`, `price_numeric`, `currency`, `rating`, `reviews_count`, `product_url`, `image_url`.
