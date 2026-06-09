# SADDL Source Mapping

This file captures the actual upstream SADDL integration points discovered from
`C:\Users\ajayg\saddl2.0-main`, as required by section `0. Read This First` of
the PRD.

## DB Access Pattern

- SADDL does not expose `get_supabase_client`.
- SADDL uses `app_core.db_manager.get_db_manager()`.
- In live mode that factory returns `app_core.postgres_manager.PostgresManager`.

## Client Identity Pattern

- SADDL consistently scopes operational data by `client_id`.
- SP-API linkage uses `public_client_id` in the upstream raw table.

## SP-API Link Table

- Table: `sc_raw.spapi_account_links`
- Relevant fields observed:
  - `public_client_id`
  - `is_active`

Used by:
- `PostgresManager.has_active_spapi_integration(client_id)`

## Listings / Own Price Source

- Table: `sc_raw.fba_inventory`
- Relevant fields observed:
  - `client_id`
  - `asin`
  - `snapshot_date`
  - `your_price`
  - `sku`

Current SADDL note:
- the pipeline writes into `your_price`, though the current ingestion code path
  appears to be populating many inventory fields before full price population.

## Performance Source

- Raw table: `sc_raw.sales_traffic`
- Relevant fields observed:
  - `account_id`
  - `child_asin`
  - `units_ordered`
  - `sessions`
  - `ordered_revenue`
  - `page_views`
  - `report_date`

## Derived Commerce View

- View: `commerce_metrics`
- Built in `app_core/postgres_manager.py`
- Relevant fields observed:
  - `client_id`
  - `asin`
  - `sku`
  - `ordered_revenue`
  - `units_ordered`
  - `sessions`
  - `organic_cvr`
  - `days_of_supply`
  - `fulfillable_quantity`
  - `total_inventory`

## Implication For This Standalone Project

The standalone project uses `pb_*` equivalents rather than directly coupling to
SADDL tables, but these upstream names are the correct reference model for any
future import/sync integration.
