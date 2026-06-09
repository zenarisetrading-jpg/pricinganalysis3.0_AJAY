# 🧭 Pricing Intelligence & Benchmarking Suite — System Architecture & Technical Deep-Dive

Welcome to the comprehensive technical documentation for the **Pricing Intelligence Suite**. This system is comprised of two core projects that work in harmony (or can run independently) to provide high-performance competitor scraping, price benchmarking, and automated strategy recommendations for marketplace listings (specifically targetting Amazon UAE & KSA):

1. **`pricing_analysis` (FastAPI + Supabase + PostgreSQL + Apify)**: The production backend system that orchestrates live Amazon scraping, external database syncing (SADDL Postgres), automated daily benchmarks, database-driven caching, ACoS-guarded recommendations, and a web-based client dashboard.
2. **`pricing-intelligence-dashboard-main` (Streamlit + Python Core)**: A user-friendly, highly visual business dashboard that operates on local spreadsheet uploads (CSVs from SellerApp/Apify) to run identical offline outlier trimming, segmentations, and pricing strategy simulations matching legacy Excel/VBA calculations.

---

## 🏗️ Core Architecture Overview

Below is a system architecture diagram that visualizes how the databases, external APIs, scraped data feeds, FastAPI backend, and Streamlit frontend coordinate together:

```mermaid
graph TD
    %% Databases and APIs
    subgraph External Systems
        SADDL[External SADDL PostgreSQL DB]
        Apify[Apify Amazon Scraper Client]
    end

    subgraph Supabase Database [Supabase Cloud Database]
        EventsTable[pb_price_events (Tier 1)]
        SnapDailyTable[pb_client_snapshots_daily (Tier 2)]
        SnapPriceTable[pb_price_snapshots_daily (Tier 2 Archive)]
        RecsTable[pb_recommendations (Tier 3)]
        AlertsTable[pb_alerts (Tier 3)]
        CompetitorsTable[competitor_products / pb_category_competitors]
        SettingsTable[pb_settings]
    end

    %% FastAPI Backend
    subgraph FastAPI Backend [pricing_analysis Server]
        Router[routes.py]
        SaddlDB[saddl_db.py]
        SnapshotSvc[snapshot_service.py]
        DiscoverySvc[discovery_service.py]
        RelevanceFilter[relevance_filter.py]
        ApifyClient[apify_client.py]
        AlertsEngine[alerts.py]
        RecsEngine[recommendations.py]
        Benchmarking[benchmarking.py]
        Nightly[nightly.py]
        WebUI[price_benchmarking.html]
    end

    %% Streamlit Local App
    subgraph Streamlit Local App [pricing-intelligence-dashboard-main]
        AppStreamlit[app.py]
        PricingTool[pricing_tool.py]
        UploadCSVs[SellerApp / Noon CSV Uploads]
    end

    %% Connections
    SADDL -->|psycopg2 pool| SaddlDB
    SaddlDB -->|Account & Catalog Synced| Router
    Apify -->|Triggered Residential Crawler| ApifyClient
    ApifyClient -->|ASIN Lists / Keywords| Apify
    Apify -->|Async Dataset Webhook| Router
    Router -->|Raw Events Ingested| EventsTable
    Router -->|Triggers Snapshot Calculations| SnapshotSvc
    
    SnapshotSvc -->|Relevance Keywords Check| RelevanceFilter
    SnapshotSvc -->|Calculate Positions| Benchmarking
    SnapshotSvc -->|Evaluate Flag Severity| AlertsEngine
    SnapshotSvc -->|ACoS Guarded Engine| RecsEngine
    
    SnapshotSvc -->|Writes Daily Runs| SnapDailyTable
    SnapshotSvc -->|Writes Alert Flag logs| AlertsTable
    SnapshotSvc -->|Writes Actionable Recommendations| RecsTable
    
    Nightly -->|Daily Cron Job| SnapPriceTable
    Nightly -->|Purge Old Events| EventsTable

    WebUI -->|Interacts with Rest API| Router
    UploadCSVs -->|Multi-file Local CSV Parse| AppStreamlit
    AppStreamlit -->|Applies VBA-Parity Algorithms| PricingTool
    PricingTool -->|Outlier Trimming & Segmentations| AppStreamlit
```

---

## 📂 Deep Dive: Repository File Catalogs

### 1️⃣ Production Backend System (`pricing_analysis`)

This repository forms the live, persistent server-side application. It utilizes a three-tier architecture (Raw Events $\rightarrow$ Aggregations $\rightarrow$ Recommendations/Alerts) powered by FastAPI and Supabase.

#### 📄 [main.py](file:///d:/pricing_analysis/main.py)
* **Purpose**: The entry point for the FastAPI application.
* **Core Functionality**:
  * Initializes the `FastAPI` instance.
  * Mounts the price benchmarking router `/api/v1/benchmarking` from `features/price_benchmarking/routes.py`.
  * Exposes a `/health` health-check route for standard uptime monitoring.
  * Exposes the `/benchmarking` route, serving the HTML-native frontend dashboard (`dashboard/price_benchmarking.html`) to web clients.
* **How it links**: Acts as the global orchestrator routing all HTTP requests directly to the business features.

#### 📄 [db.py](file:///d:/pricing_analysis/db.py)
* **Purpose**: Creates and manages the connection to Supabase.
* **Core Functionality**:
  * Loads environment variables from `.env` (`SUPABASE_URL`, `SUPABASE_KEY`).
  * Exports `get_supabase_client()`, which uses `lru_cache(maxsize=1)` to instantiate and share a single cached thread-safe client across the server threads.
* **How it links**: Imported by all routes and service modules that require direct CRUD access to Supabase tables.

#### 📄 [auth.py](file:///d:/pricing_analysis/auth.py)
* **Purpose**: Simple authorization and client identification provider.
* **Core Functionality**:
  * Defines `get_current_client_id(request, x_client_id)`.
  * Extracts client credentials in a prioritized, fallback manner:
    1. Case-insensitive custom header: `X-Client-Id`.
    2. URL Query parameter: `client_id` (used if downstream API gateways strip headers).
    3. Local environment variable fallback: `DEFAULT_CLIENT_ID`.
  * Raises a `401 Unauthorized` exception if no client identity is resolvable.
* **How it links**: Injected as a dependency (`Depends(get_current_client_id)`) across secure FastAPI routes.

#### 📄 [features/price_benchmarking/routes.py](file:///d:/pricing_analysis/features/price_benchmarking/routes.py)
* **Purpose**: Declares all REST API endpoints for discovery, scraping, onboarding, and dashboard populating.
* **Core Functionality**:
  * Handles Apify Webhooks (`/webhook/apify`) for parsing and storing raw scraped competitor data.
  * Houses endpoints `/accounts` and `/account-bsr-categories` that connect to the external SADDL Postgres DB via `saddl_db.py`.
  * Implements `/trigger-competitor-analysis` which initiates full background scraping or returns cached results.
  * Contains manual override handlers for listings `/listings` (strategies, min/max price margins, exclude terms) and category scrapes `/trigger-category-scrape`.
  * Exposes `/overview` which returns highly structured summaries matching parent ASIN titles and reference names for the client dashboard.
* **How it links**: Calls services like `discovery_service`, `snapshot_service`, and `apify_client`, mapping raw web requests directly to backend services.

#### 📄 [features/price_benchmarking/saddl_db.py](file:///d:/pricing_analysis/features/price_benchmarking/saddl_db.py)
* **Purpose**: Low-level Postgres bridge querying the main SADDL relational catalog database.
* **Core Functionality**:
  * Manages a psycopg2 connection pool (`SimpleConnectionPool`) configured strictly in read-only transaction mode for security.
  * Implements `execute_saddl_query` with automatic connection-loss reset and a single-retry recovery logic.
  * Retrieves:
    * Active clients (`fetch_saddl_accounts`).
    * Product variations mapping, including parent/child ASIN relationships, brands, titles, and BSR category data (`fetch_account_products_with_categories`).
    * Recent average selling prices and live historical FBA inventory catalogs (`fetch_account_prices`).
    * Performance records: Units ordered, traffic sessions, ordered revenue, CV% (conversion rate), and ad spend/sales statistics (`fetch_account_performance`).
* **How it links**: Supplies catalogs and live store performance data to `routes.py` and `discovery_service.py` to seed calculations.

#### 📄 [features/price_benchmarking/snapshot_service.py](file:///d:/pricing_analysis/features/price_benchmarking/snapshot_service.py)
* **Purpose**: Orchestrates the statistical calculations, pricing zones, and database snapshots for a client portfolio.
* **Core Functionality**:
  * Integrates `benchmarking.py` (calculations), `alerts.py` (warnings), and `recommendations.py` (repricing values) together.
  * Filters raw scraped data from `pb_price_events` according to candidate brand overrides (`pb_client_competitor_overrides`) and relevance keyword filters (`relevance_filter.py`).
  * Implements `calculate_transient_upload_analysis` to compute pricing snapshots dynamically in-memory without saving them to the database (used during spreadsheet upload dry-runs).
  * Exposes `_resolve_majority_categories` to group variation ASINs under their parent, identify the dominant category, and clean up conflicting categories.
* **How it links**: Driven by `routes.py` webhooks and the `discovery_service.py` workflow to persist Tier 2 snapshots and Tier 3 alert files.

#### 📄 [features/price_benchmarking/discovery_service.py](file:///d:/pricing_analysis/features/price_benchmarking/discovery_service.py)
* **Purpose**: Provides high-level workflows for competitor product discovery and database-centric caching.
* **Core Functionality**:
  * Defines `run_competitor_analysis_workflow` and `trigger_background_discovery`.
  * Fetches catalog listings from SADDL database, identifies missing competitors, and invokes Apify category scans.
  * Saves results to `competitor_products` and aggregates them onto `pb_client_snapshots_daily` and `pb_recommendations` at the parent ASIN level.
  * Implements `recalculate_parent_from_categories` to re-run calculations for a parent ASIN from its local category pool, immediately clearing stale recommendations.
* **How it links**: Invoked by routes when users trigger analyses, utilizing `apify_client.py` and `snapshot_service.py` internally.

#### 📄 [features/price_benchmarking/relevance_filter.py](file:///d:/pricing_analysis/features/price_benchmarking/relevance_filter.py)
* **Purpose**: String parsing and matching algorithm ensuring only relevant products enter calculations.
* **Core Functionality**:
  * Implements `calculate_relevance_score(reference_name, candidate_title)`.
  * Features the comma-delimited `OR` and space-delimited `AND` parser.
  * Implements `match_brand` to exclude competing listings from specified brands, using space normalization and regex word-boundaries to prevent greedy matches.
  * Implements `filter_related_products` to clean competitor ASIN pools based on keywords and target rules.
* **How it links**: Called inside `snapshot_service.py` to filter competitor datasets down to genuine matches.

#### 📄 [features/price_benchmarking/apify_client.py](file:///d:/pricing_analysis/features/price_benchmarking/apify_client.py)
* **Purpose**: Python client encapsulating all interactions with the Apify Crawler actor.
* **Core Functionality**:
  * Wraps `ApifyClient` and launches `"junglee/amazon-crawler"`.
  * Provisions residential proxy routing specific to country codes (`AE` for UAE, `SA` for KSA).
  * Includes automated webhook triggers on actor run completion, returning payloads back to the FastAPI `/webhook/apify` endpoint.
  * Defines `parse_apify_item` to extract ASINs, clean prices from multiple places (buy box, variants, A+ text), standardize currencies, and extract ratings/review counts.
* **How it links**: Invoked by `discovery_service` and `routes` to queue Amazon crawls.

#### 📄 [features/price_benchmarking/alerts.py](file:///d:/pricing_analysis/features/price_benchmarking/alerts.py)
* **Purpose**: Generates and severity-scores price alerts.
* **Core Functionality**:
  * Compares calculated snapshots against the previous day's metrics.
  * Flags:
    * `floor_breach`: If our price falls below the cheapest competitor.
    * `ceiling_breach`: If our price is higher than the absolute ceiling.
    * `competitor_drop`: If a competitor floor dropped significantly compared to the prior day.
* **How it links**: Imported and called inside `snapshot_service.py` to write warnings to `pb_alerts`.

#### 📄 [features/price_benchmarking/recommendations.py](file:///d:/pricing_analysis/features/price_benchmarking/recommendations.py)
* **Purpose**: Engine determining final suggested repricing values.
* **Core Functionality**:
  * Formulates recommended prices across strategies: Value, Mid, Premium, Floor, and Custom.
  * Applies `min_price` and `max_price` margins to prevent under-pricing or over-pricing.
  * Employs the **ACoS Guard**: If the engine suggests a price decrease but historical advertising data shows an average ACoS > 35%, it suppresses the decrease and holds the price.
* **How it links**: Executed within `snapshot_service.py` to generate files written to `pb_recommendations`.

#### 📄 [features/price_benchmarking/benchmarking.py](file:///d:/pricing_analysis/features/price_benchmarking/benchmarking.py)
* **Purpose**: Core mathematical operations for marketplace position benchmarking.
* **Core Functionality**:
  * Implements `compute_benchmark` to sort competitor prices and calculate the floor, ceiling, median, mean, p25, and p75.
  * Determines our marketplace positioning index: `index_vs_median = (your_price / median) * 100`.
  * Computes percentile ranks and classifies listings into `PriceZone` groups (Below Market, Budget, Value, Mid-Market, Premium, Above Market).
* **How it links**: The mathematical engine undergirding both `snapshot_service.py` and `recommendations.py`.

#### 📄 [features/price_benchmarking/nightly.py](file:///d:/pricing_analysis/features/price_benchmarking/nightly.py)
* **Purpose**: Daily automated aggregation and clean-up tasks.
* **Core Functionality**:
  * Aggregates raw price logs from the previous day into standard daily records (`pb_price_snapshots_daily`).
  * Purges old files: Deletes raw `pb_price_events` older than 90 days to optimize database size.
* **How it links**: Invoked by a daily cron job targeting the `/nightly` FastAPI route.

---

## 📂 Deep Dive: Repository File Catalogs

### 2️⃣ Offline Simulation Tool (`pricing-intelligence-dashboard-main`)

This repository is designed for offline, spreadsheet-driven workflows. It processes uploaded CSV files directly inside a Streamlit application, mimicking Excel/VBA calculations.

#### 📄 [app.py](file:///d:/pricing-intelligence-dashboard-main/app.py)
* **Purpose**: Streamlit dashboard frontend and local entry point.
* **Core Functionality**:
  * Renders a sidebar for uploading multiple CSV exports (from tools like SellerApp) and configuring inputs (strategy, brand filters, break-even price, and margins).
  * Cleans price data, runs matching exclusions, and runs both regular and deduped calculations.
  * Displays interactive data tables and exports raw summaries and brand metrics back to CSV.
  * Employs a Plotly scatter chart that maps Median Price vs. Median CCS for all brands, including interactive histograms across price, CCS, stars, and reviews.
* **How it links**: Loads and routes raw pandas DataFrames into the analytical engine in `pricing_tool.py`.

#### 📄 [pricing_tool.py](file:///d:/pricing-intelligence-dashboard-main/pricing_tool.py)
* **Purpose**: The data processing engine of the Streamlit application.
* **Core Functionality**:
  * Automatically detects price, rating, reviews, health, and BSR columns.
  * Computes the **Composite Competitor Score (CCS)**, normalizing listing health, ratings, reviews, and inverse BSR to a 0.0 - 1.0 score.
  * Applies **Excel-parity Interquartile Trim (IQT)** using nearest-rank percentiles (5th-95th) to eliminate price outliers.
  * Implements `match_brand` to exclude competing listings from specified brands.
  * Groups listings at the brand level to calculate brand medians, assigns brands to market tiers (Entry, Mass, Mid-Premium, Premium), and returns price recommendations based on the target strategy.
* **How it links**: Imported directly by `app.py` (`import pricing_tool as core`) to process and segment uploaded data.

---

## 📈 Key Algorithms & Mathematical Logic

### 1️⃣ Composite Competitor Score (CCS)
The Composite Competitor Score (CCS) measures a competitor's marketplace strength. It maps four performance vectors onto a normalized value between $0.0$ (weakest) and $1.0$ (strongest) using the following weights:

$$\text{CCS} = 0.35 \times \text{Reviews}_{\text{norm}} + 0.30 \times \text{Rating}_{\text{norm}} + 0.20 \times \text{Health}_{\text{norm}} + 0.15 \times \text{BSR}_{\text{norm\_inv}}$$

* **BSR Inverse**: BSR ranks are lower-is-better. Thus, BSR is converted using:
  $$\text{BSR}_{\text{inv}} = \frac{1}{\max(1, \text{BSR})}$$
* **Normalization Function**:
  $$\text{Value}_{\text{norm}} = \frac{\text{Value} - \min(\text{Series})}{\max(\text{Series}) - \min(\text{Series})}$$
  *(If the series contains identical values, the score defaults to $0.5$)*

### 2️⃣ Excel-Parity Outlier Trim (IQT)
To mirror Excel/VBA's percentile trimming, the system uses a **nearest-rank** approach to establish the 5th and 95th percentiles:

1. Sort $N$ prices in ascending order: $P_0, P_1, \dots, P_{N-1}$.
2. Calculate nearest indices for boundaries:
   $$\text{Index}_{\text{low}} = \lfloor 0.05 \times (N - 1) \rfloor$$
   $$\text{Index}_{\text{high}} = \lceil 0.95 \times (N - 1) \rceil$$
3. Extract bound values:
   $$\text{Price}_{\text{floor}} = P_{\max(0, \text{Index}_{\text{low}})}$$
   $$\text{Price}_{\text{ceiling}} = P_{\min(N - 1, \text{Index}_{\text{high}})}$$
4. Retain all listings with prices within this range: $[\text{Price}_{\text{floor}}, \text{Price}_{\text{ceiling}}]$.

### 3️⃣ Relevance & Exclusion Query Matching
* **Reference Name Parsing**:
  * The `reference_name` represents target keywords. Comma characters (`,`) behave as `OR` operators, splitting queries into alternative matches.
  * Space characters (` `) inside each phrase behave as `AND` operators. Every space-separated term must appear in the competitor's title for it to match.
  * **Example**: `kids water bottle, bento box` matches any listing containing BOTH `kids` and `water` and `bottle`, OR any listing containing BOTH `bento` and `box`.
* **Exclusion Parsing**:
  * An `exclude_keywords` string splits on `|brand_exclude:` to isolate regular keywords from brand exclusions.
  * Brand exclusions undergo whitespace normalization and are matched via case-insensitive regex word-boundary filters:
    $$\text{Pattern} = \text{re.compile}(r"\b" + \text{re.escape(brand)} + r"\b", \text{re.IGNORECASE})$$
    This prevents accidental matches (e.g., excluding the brand `Stan` won't accidentally exclude `Stanley` listings).

### 4️⃣ ACoS-Guarded Pricing Strategies
Once the competitor pool is filtered, a target anchor price $A$ (the median price of the selected tier) is established. The target price is calculated based on the strategy:

| Repricing Strategy | Mathematical Definition | Description |
| :--- | :--- | :--- |
| **Mid (Align)** | $A$ | Price at par with median |
| **Value** | $\frac{\text{Floor} + \text{P25}}{2}$ | Lower band to capture volume |
| **Premium** | $\frac{\text{P75} + \text{Ceiling}}{2}$ | High positioning for premium branding |
| **Floor** | $\text{Floor} \times (1 - 0.02)$ | Undercut cheapest competitor by 2% |
| **Custom** | $\text{Custom Target}$ | User-defined target price |

* **Min/Max Pricing bounds**:
  $$\text{Price}_{\text{bounded}} = \max(\text{MinPrice}, \min(\text{MaxPrice}, \text{Price}_{\text{target}}))$$
* **ACoS Guard Condition**:
  If the calculated action is a price decrease ($P_{\text{new}} < P_{\text{current}}$) but the product's average advertising ACoS $> 35\%$, the price change is suppressed:
  $$\text{Action}_{\text{final}} = \text{Hold}$$
  $$\text{Price}_{\text{final}} = P_{\text{current}}$$

### 5️⃣ Majority Category Resolution
Amazon variation listings (different colors/sizes under one parent ASIN) can sometimes be assigned to conflicting categories in BSR records. To keep analysis pools consistent:
1. Variations are grouped by `parent_asin`.
2. The frequency of category assignments across all child ASINs is counted.
3. The category with the majority count is declared the winner (alphabetical sorting breaks ties).
4. All child variations are updated to the winning category's ID and name.

---

## 🔄 End-to-End System Workflows

### Flow A: API-Driven Automated Competitor Scraping & Analysis
This automated backend workflow coordinates live data collection and updates:

```
[FastAPI Router]
       │  (1) /trigger-competitor-analysis
       ▼
[Discovery Service] ──(2) Read internal listings──► [psycopg2 / SADDL DB]
       │
       ├──(3) Identify missing categories
       ▼
[Apify Client] ──(4) Start Amazon crawler crawl ──► [Apify Cloud Actor]
                                                            │
                                                     (Execution)
                                                            │
[FastAPI Router] ◄──(5) POST webhook event dataset ◄────────┘
       │
       ├──(6) Ingest raw records into pb_price_events (Tier 1)
       │
       └──(7) Trigger snapshot calculation in background thread
                    │
                    ▼
            [Snapshot Service] ──(8) Resolve child-to-parent mappings
                    │
                    ├──(9) Apply brand & keyword relevance filters
                    │
                    ├──(10) Run statistical benchmarks & positioning indices
                    │
                    ├──(11) Apply strategies and check ACoS Guard
                    │
                    └──(12) Save outputs to tables:
                                 ├── pb_client_snapshots_daily (Tier 2)
                                 ├── pb_alerts (Tier 3)
                                 └── pb_recommendations (Tier 3)
```

---

### Flow B: Spreadsheet-Driven Local Streamlit Analysis
This offline business workflow operates entirely within the Streamlit dashboard:

```
[Local Business User]
       │
       ├──(1) Upload one or more SellerApp CSV exports
       ├──(2) Configure intended strategy, target margins, and break-even
       └──(3) Click "Run Analysis"
                    │
                    ▼
            [app.py (Streamlit)]
                    │
                    ├──(4) Combine multiple CSV files into a unified Pandas DataFrame
                    ├──(5) Strip currency symbols and clean price columns
                    ▼
            [pricing_tool.py]
                    │
                    ├──(6) Perform IQT 5-95 nearest-rank outlier trimming
                    ├──(7) Compute Composite Competitor Score (CCS) for listings
                    ├──(8) Segment brands into quartile market tiers
                    ├──(9) Calculate recommended prices matching strategy rules
                    ▼
            [app.py (Streamlit)]
                    │
                    ├──(10) Render primary recommendation metric cards
                    ├──(11) Draw interactive Plotly scatter plots and histograms
                    └──(12) Generate download links for metrics & summaries
```

---

## 🗄️ Database Tables (Supabase Schema)

* **`pb_price_events` (Tier 1)**: Stores raw scraped competitor records, including ASIN, floor_price, buy_box_price, seller_name, is_buy_box_winner, shipping_price, BSR, and scraped_at.
* **`pb_client_snapshots_daily` (Tier 2)**: Stores daily benchmarking snapshots for client products, including n_competitors, floor_price, ceiling_price, median_price, p25/p75 prices, positioning index, and price zone.
* **`pb_price_snapshots_daily` (Tier 2 Archive)**: Stores historical market pricing averages aggregated from raw price events during the nightly cron job.
* **`pb_recommendations` (Tier 3)**: Actionable pricing changes (current price, recommended price, change percentage, reasoning, confidence level, and execution status).
* **`pb_alerts` (Tier 3)**: Daily alert flags raised when pricing breaches occur.
* **`competitor_products` / `pb_category_competitors`**: Catalogs and filters discovered competitor ASINs, assigning them to categories and calculating their relevance scores.
* **`pb_settings`**: Global system parameters (e.g. enabling or disabling scraping automation).

---

© 2026 **S2C Lifestyle & SADDL Solutions** — Confident Business Engineering.
