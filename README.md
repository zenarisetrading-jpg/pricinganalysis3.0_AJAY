# SADDL Price Benchmarking v3 (Apify-Native)

High-performance price benchmarking for Amazon UAE and KSA, leveraging Apify for competitor intelligence and SP-API for internal listing management.

## 🚀 Key Features
- **Apify-Native Pipeline**: Asynchronous scraping using residential proxies to bypass Amazon's anti-bot protections.
- **Rich Market Intelligence**: Captures `seller_name`, `is_buy_box_winner`, and `shipping_price`.
- **Asynchronous Webhooks**: Real-time data ingestion via FastAPI `/webhook/apify` endpoint.
- **3-Tier Data Architecture**: Robust history and performance tracking in Supabase.

## 📂 Project Layout
- `features/price_benchmarking/` - Core logic, routes, and services.
- `dashboard/` - Frontend UI.
- `supabase/migrations/` - Database schema and migrations.
- `tests/` - Unit tests for core math and aggregation logic.

## 🛠️ Getting Started
1. **Environment Setup**:
   - Copy `.env.example` to `.env`.
   - Add your `SUPABASE_URL`, `SUPABASE_KEY`, and `APIFY_TOKEN`.
2. **Database Migration**:
   - Apply the SQL migrations in `supabase/migrations/` to your Supabase project.
3. **Run the Server**:
   ```bash
   uvicorn main:app --reload
   ```
4. **Configure Webhook**:
   - In the Apify Console, set the "Run Succeeded" webhook URL for your Amazon crawler to:
     `https://your-domain.com/api/v1/benchmarking/webhook/apify`

## 🤖 API Reference
- `POST /api/v1/benchmarking/trigger-scrape`: Start a market-wide scrape.
- `POST /api/v1/benchmarking/webhook/apify`: Asynchronous ingestion entry point.
- `POST /api/v1/benchmarking/discover-competitors`: Seed new ASINs via category search.
- `GET /api/v1/benchmarking/overview`: Fetch latest market positioning data.

## 🧪 Verification
Run unit tests:
```bash
pytest tests/
```
