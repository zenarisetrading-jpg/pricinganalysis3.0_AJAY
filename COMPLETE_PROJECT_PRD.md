# SADDL Pricing Intelligence & Benchmarking Suite — Complete End-to-End PRD

## 1. Project Overview
**Purpose:** The SADDL Pricing Intelligence Suite is designed to provide high-performance competitor scraping, price benchmarking, and automated strategy recommendations for Amazon marketplace listings (specifically targetting UAE & KSA).
**Business Objective:** Automate the process of discovering competitors, tracking market pricing in real-time, computing benchmark metrics (floor, median, ceiling), and intelligently recommending pricing adjustments (with ACoS guards) to maintain a competitive edge.
**Target Users:** 
- Own brands (e.g., S2C/Zenarise) running their own Amazon accounts.
- Agency clients (e.g., boutique Amazon PPC agencies) managing multiple seller accounts.
**Core Modules:** 
- Backend API (FastAPI)
- Competitor Discovery & Scraping (Scrapergraph, crawl4ai)
- Business Logic & Benchmarking (Python Services)
- Frontend Dashboard (HTML/JS)
- Database (Supabase PostgreSQL, external SADDL Postgres)
**Overall Architecture:** A multi-tier system capturing raw market events, computing daily client pricing snapshots, raising alerts, and surfacing intelligent pricing recommendations through a dashboard.

---

## 2. Technology Stack

**Frontend**
- **Framework / UI:** Pure HTML, CSS (Custom styling with glassmorphism and modern UI), Vanilla JavaScript.
- **Charts:** ApexCharts (via CDN).
- **Routing:** Single Page App (SPA) logic handled natively via JS hash/display toggling.
- **State Management:** Local JS objects and DOM dataset management.
- **Styling:** Vanilla CSS with CSS Variables.

**Backend**
- **Framework:** FastAPI (Python).
- **API Architecture:** RESTful APIs with route segregation (`/api/v1/benchmarking`).
- **Authentication:** Custom header/query param validation (`X-Client-Id`, `client_id`).
- **Business Services:** Modular Python files (`benchmarking.py`, `recommendations.py`, `alerts.py`, etc.).

**Database**
- **Database Engine:** PostgreSQL hosted on Supabase.
- **Schema Usage:** Three-tiered architecture (Raw Events -> Aggregated Snapshots -> Recommendations).
- **External Database:** SADDL Postgres for client catalog/performance data (read-only via `psycopg2`).

**Infrastructure**
- **Environment Variables:** Loaded via `.env`.
- **Deployment Architecture:** Railway (App Hosting & Cron Jobs).
- **External Services:** Scrapergraph (primary) and Crawl4ai (secondary) for scraping.

---

## 3. High-Level Architecture

User
↓
Frontend (dashboard/price_benchmarking.html)
↓
API Layer (FastAPI Routers in features/price_benchmarking/routes.py)
↓
Business Logic (snapshot_service, discovery_service, benchmarking)
↓
Database (Supabase DB + SADDL DB)
↓
Response (JSON structure)
↓
Frontend Rendering (Vanilla JS DOM Updates & ApexCharts)

---

## 4. Complete Application Flow

User opens application (`/benchmarking` endpoint serving HTML)
↓
Authentication (Client ID verified via headers/query params)
↓
Dashboard loads
↓
Frontend calls APIs (`/accounts`, `/overview`, etc.)
↓
Backend validates request
↓
Business logic executes (Fetching from Supabase or triggering calculation)
↓
Database queried (Fetching tier 2/3 snapshots)
↓
Response returned (JSON)
↓
Frontend renders tables and KPI cards
↓
Graphs generated via ApexCharts
↓
User applies filters (e.g. brand exclusion, strategy change)
↓
New API request to backend to trigger analysis
↓
Calculations performed dynamically
↓
Updated UI displayed

---

## 5. Module-by-Module Flow

### Scraping & Discovery Module
- **Purpose:** Find competitor ASINs and their live prices.
- **User actions:** Can trigger manual scrape or rely on automated night cron.
- **API calls:** `/trigger-scrape`, `/discover-competitors`, `/webhook/scrapergraph`
- **Backend processing:** `scraper_client.py` sends request to Scrapergraph/Crawl4ai; FastAPI webhook receives scraped data asynchronously.
- **Database queries:** Inserts raw prices into `pb_price_events`.
- **Business rules:** Requires residential proxies for UAE/KSA.
- **Returned data:** `status`, `dataset_id`.

### Benchmarking & Snapshot Module
- **Purpose:** Compute percentiles and price positioning.
- **Frontend flow:** Triggered implicitly by viewing data or manually applying filters.
- **Backend processing:** `snapshot_service.py` and `benchmarking.py` compute floor, ceiling, median, p25, p75.
- **Database queries:** Upserts into `pb_client_snapshots_daily`.
- **Business rules:** Excludes outliers using interquartile trims.

### Recommendations Module
- **Purpose:** Suggest new prices.
- **Backend processing:** `recommendations.py` evaluates strategies (Value, Mid, Premium, Floor) with bounds.
- **Business rules:** ACoS Guard (prevents price drops if ACoS > 35%).
- **Database queries:** Writes to `pb_recommendations`.

---

## 6. Frontend Architecture
- **Folder structure:** Located primarily in `dashboard/` (e.g., `price_benchmarking.html`).
- **Pages/Layouts:** A single integrated view with a Sidebar navigation and a main content area.
- **Shared components:** Native HTML elements styled via CSS classes (glass panels, data tables).
- **State management:** Variables in script tags holding current selections.
- **Charts:** Rendered using ApexCharts instance variables.
- **Error handling:** `try/catch` around `fetch()` calls, mapping to alert dialogs.
- **Responsive behavior:** CSS Media Queries.

---

## 7. Backend Architecture
- **Folder structure:** Features-based (`features/price_benchmarking/`).
- **Routers:** `routes.py`
- **Services:** `discovery_service.py`, `snapshot_service.py`
- **Utilities:** `relevance_filter.py`, `scraper_client.py`
- **Middleware/Auth:** `auth.py` validating `X-Client-Id`.
- **Business calculations:** `benchmarking.py` for stats, `recommendations.py` for pricing rules.
- **Logging/Exception handling:** FastAPI HTTPExceptions.

---

## 8. Database Documentation
- **Tier 1:** `pb_price_events` - Raw Scrapergraph/Crawl4ai scrape data (90-day TTL).
- **Tier 2:** `pb_price_snapshots_daily` (permanent archive), `pb_client_snapshots_daily` (client-specific benchmark results).
- **Tier 3:** `pb_recommendations` (pricing suggestions), `pb_alerts` (breaches).
- **Metadata:** `competitor_products` / `pb_category_competitors` for ASIN tracking.
- **Relationships:** Clients -> Products -> Competitors -> Price Events.

---

## 9. Data Population Flow
1. **API Called:** Dashboard JS calls `/overview`.
2. **Backend Function:** `routes.py` handles the GET request.
3. **Service:** Queries Supabase `pb_client_snapshots_daily` and `pb_recommendations`.
4. **Calculations:** Combines database snapshots with active alerts.
5. **JSON Built:** Returns list of structured metrics for the client.
6. **Frontend Consumes:** JS `fetch` resolves.
7. **Component Render:** DOM elements (cards, tables) updated.
8. **Graphs:** ApexCharts `.updateSeries()` called with new arrays.

---

## 10. API Documentation
- **POST `/trigger-scrape`**: Triggers Scrapergraph crawler. Accepts `marketplace`, `asins`. Returns dataset info.
- **POST `/webhook/scrapergraph`**: Scrapergraph posts results here. Validates dataset, inserts to `pb_price_events`, triggers background benchmark computation.
- **GET `/overview`**: Returns JSON of all daily snapshots, alerts, and recommendations for the authenticated client.

---

## 11. Business Logic Documentation
- **Composite Competitor Score (CCS):** Weighted score (0-1) based on Reviews (35%), Rating (30%), Health (20%), and Inverse BSR (15%).
- **Interquartile Trim (IQT):** Nearest-rank approach to establish 5th and 95th percentiles to eliminate outlier prices.
- **ACoS Guard:** If strategy suggests a price decrease but ACoS > 35%, the engine overrides the recommendation to "Hold" the current price.

---

## 12. User Journey
Login (Pass Client ID)
↓
Open Dashboard
↓
Dashboard automatically queries `/overview`
↓
Frontend parses JSON and populates Charts & Tables
↓
User selects "Trigger Scrape"
↓
Backend queries Scrapergraph
↓
Scrapergraph Webhook returns data
↓
Backend updates Snapshots & Recommendations
↓
User refreshes or UI polls to see new Recommendations

---

## 13. Sequence Diagrams (Text)
User
↓ (Click "Run Scrape")
React/HTML Component
↓ (POST /trigger-scrape)
FastAPI Router
↓ 
Scraper Client
↓ 
Scrapergraph / Crawl4ai
↓ (Webhook POST)
FastAPI Router
↓
Snapshot Service (Background)
↓ 
Supabase Database (Insert pb_price_events)

---

## 14. Data Flow Diagrams
Input (Category URL)
↓
Validation (FastAPI)
↓
Scrapergraph Scraping
↓
Transformation (`parse_scraped_item` formatting to AED/SAR, floats)
↓
Database (`pb_price_events`)
↓
Business Logic (`benchmarking.py`)
↓
Database (`pb_client_snapshots_daily`)

---

## 15. Component Mapping
- **UI Component:** Overview Table
- **API:** `/overview`
- **Backend Function:** Queries Tier 3 tables.
- **Database Tables:** `pb_client_snapshots_daily`, `pb_recommendations`.
- **Displayed Elements:** Rows showing ASIN, Your Price, Market Median, Recommended Price.

---

## 16. State Management
- **Global state:** `X-Client-Id` stored locally for requests.
- **Local state:** Active filters (brand exclusions, selected marketplace) held in JS variables.
- **Loading:** CSS spinners toggled on DOM nodes during `fetch` promises.

---

## 17. Authentication Flow
- **Mechanism:** Simple identity verification.
- **Flow:** API endpoints depend on `get_current_client_id` from `auth.py`. 
- Checks `X-Client-Id` header -> `client_id` query param -> `DEFAULT_CLIENT_ID` env.
- Fails with 401 if missing.

---

## 18. Error Handling
- **Frontend:** API fetch failures catch block triggers UI alert/toast.
- **Backend:** Missing datasets, invalid scraping params result in `HTTPException(400)`.
- **Scraping failures:** Residential proxy failures return empty datasets, handled gracefully.

---

## 19. External Integrations
- **Supabase:** Primary DB for Tier 1/2/3 data.
- **Scrapergraph / Crawl4ai:** Used for competitor discovery and pricing.
- **SADDL Postgres:** External DB for client configurations and legacy performance catalogs.

---

## 20. Environment Configuration
- `SUPABASE_URL`, `SUPABASE_KEY`
- `SCRAPERGRAPH_TOKEN` / `CRAWL4AI_TOKEN` (Critical for Railway cron)
- Managed securely in Railway for Prod, `.env` for Dev.

---

## 21. Performance Flow
- **Batch queries:** Bulk inserts for Scrapergraph webhook results.
- **Background Tasks:** Benchmarking runs in FastApi `BackgroundTasks` to prevent webhook timeouts.
- **Data Pruning:** Nightly cron purges `pb_price_events` older than 90 days.

---

## 22. Security Flow
- **Authentication:** Validated client scopes.
- **Webhooks:** Relies on unguessable dataset IDs and HTTPS.
- **SQL Injection:** Avoided by using Supabase Python Client (PostgREST wrapper) and parameterized `psycopg2` queries.

---

## 23. Deployment Architecture
- **Build process:** Standard Python Dockerfile/Procfile.
- **Backend deployment:** Railway App.
- **Database:** Supabase Cloud.
- **Cron Jobs:** Scheduled in Railway to hit FastAPI endpoints at 2 AM (Scrape) and 10 PM (Aggregation).

---

## 24. Folder Responsibilities
- `features/`: Contains business domain logic (e.g., `price_benchmarking`).
- `dashboard/`: Contains static HTML/JS frontend assets.
- `scripts/`: Contains utility scripts or database migration testing tools.
- `scratch/`: Temporary files.

---

## 25. Glossary
- **ASIN:** Amazon Standard Identification Number.
- **BSR:** Best Sellers Rank.
- **CCS:** Composite Competitor Score.
- **IQT:** Interquartile Trim (Outlier removal).
- **Tier 1/2/3:** The cascading data model from raw scrape to client recommendation.

---

## 26. Frequently Asked Questions
- **Where does dashboard data come from?** Supabase tables populated by backend services querying Scrapergraph.
- **How are charts populated?** ApexCharts consumes JSON arrays from FastAPI endpoints.
- **How is authentication handled?** Client ID via HTTP headers.
- **Which APIs populate this page?** Mostly the `/overview` endpoint.
- **How are calculations performed?** Pandas/pure Python math in `benchmarking.py` runs standard statistical aggregation (percentiles, medians).

---

## 27. Complete End-to-End Flow Summary
User opens application → Client ID header injected → Dashboard API (`/overview`) called → Backend validates token → Business service queries Supabase Tier 3 tables → Results transformed into structured JSON → Frontend state updated → Components re-render → Charts refreshed → User applies brand filter → New `/trigger-scrape` or recalc request → Backend drops old snaphot → Business logic recalculates median without the excluded brand → Updated UI displayed. Nightly cron jobs ensure data is scraped daily via Scrapergraph using residential proxies and stale data is purged, maintaining the system asynchronously.
