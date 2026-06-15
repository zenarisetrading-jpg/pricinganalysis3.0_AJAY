# SADDL Data Migration & Integration Spec
## Target: Account & BSR Data Orchestration

This document defines the schema and implementation plan for utilizing SADDL's account and BSR (Best Seller Rank) data in an external project.

---

## 1. Core Data Structures

### 1.1 Account & Client Management
These tables identify active clients and their configuration settings.

| Table Name | Schema | Key Columns | Description |
| :--- | :--- | :--- | :--- |
| **`accounts`** | `public` | `account_id`, `account_name`, `organization_id` | Primary identity table for Amazon accounts. |
| **`client_settings`** | `public` | `client_id`, `ads_profile_id`, `sync_status` | Operational settings and API link status. |
| **`account_daily`** | `sc_analytics` | `report_date`, `total_ordered_revenue`, `tacos` | Daily performance rollup used to verify active status. |

### 1.2 BSR & Category Tracking
These tables store historical rank data and category classifications.

| Table Name | Schema | Key Columns | Description |
| :--- | :--- | :--- | :--- |
| **`bsr_history`** | `sc_raw` | `asin`, `category_name`, `rank`, `report_date` | Raw time-series data of category rankings per ASIN. |
| **`bsr_trends`** | `sc_analytics` | `asin`, `rank_change_7d`, `rank_status_7d` | **VIEW**: Computes improvements/declines in BSR. |

---

## 2. SQL Reference for Extraction

### 2.1 Fetch Active Accounts with BSR Snapshots
Use this query to get a master list of clients and their current top-ranking categories.

```sql
SELECT 
    a.account_name, 
    b.asin, 
    b.category_name, 
    b.rank AS current_bsr, 
    b.report_date AS last_updated
FROM public.accounts a
JOIN sc_raw.bsr_history b ON a.account_id = b.marketplace_id
WHERE b.report_date = (SELECT MAX(report_date) FROM sc_raw.bsr_history)
  AND a.organization_id IS NOT NULL
ORDER BY b.rank ASC;
```

### 2.2 Identify "Improving" Categories
Used to find products gaining organic momentum.

```sql
SELECT 
    asin, 
    category_name, 
    current_rank, 
    rank_7d_ago, 
    rank_status_7d
FROM sc_analytics.bsr_trends
WHERE rank_status_7d = 'IMPROVING'
ORDER BY (rank_7d_ago - current_rank) DESC;
```

---

## 3. Implementation Plan for New Project

### Phase 1: Schema Setup
1. **Replicate `sc_raw` structure**: Create the `bsr_history` table in your new database to accept raw incoming data.
2. **Setup `public` Mapping**: Create a `client_map` table that links SADDL `account_id` to your internal `user_id`.

### Phase 2: Data Ingestion (ETL)
1. **Direct Connection**: Configure a `DATABASE_URL_DIRECT` in your new project's `.env`.
2. **Nightly Sync**: Schedule a job to pull the previous day's `bsr_history` and `account_daily` records.
   * *Tool Recommendation*: Use a Python script with `psycopg2` or a Supabase Edge Function.

### Phase 3: Analytics Porting
1. **Apply BSR Trend View**: Run the `sc_analytics.bsr_trends` view definition in your new DB.
2. **Constraint Enforcement**: Ensure `UNIQUE` constraints on `(report_date, marketplace_id, asin, category_id)` are maintained to prevent duplicate rank entries.

### Phase 4: Verification & UI
1. **Health Check**: Run the "Active Accounts" query to verify data parity between SADDL and the new project.
2. **Notification Trigger**: (Optional) Setup a trigger to alert your new project when an ASIN's `rank_status_7d` shifts from `STABLE` to `DECLINING`.

---

## 4. Field Health Matrix
| Field | Data Type | Requirement | Notes |
| :--- | :--- | :--- | :--- |
| `child_asin` | `VARCHAR(20)` | Mandatory | Primary key for BSR lookups. |
| `ordered_revenue` | `NUMERIC(14,2)` | Optional | Used for revenue-weighting BSR impact. |
| `rank` | `INTEGER` | Mandatory | Lower is better. |
| `category_id` | `VARCHAR(100)`| Mandatory | Amazon-internal category string. |
