import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

# Connection pool for the external SADDL database
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        if not SADDL_DATABASE_URL:
            return None
        try:
            _pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, SADDL_DATABASE_URL,
                # Ensure read-only connection if possible via connection parameters
                options="-c default_transaction_read_only=on"
            )
        except Exception as e:
            print(f"Error creating SADDL DB pool: {e}")
            return None
    return _pool

@contextmanager
def get_db_connection():
    pool = get_pool()
    if not pool:
        yield None
        return
    
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

def execute_saddl_query(query: str, params: tuple = ()):
    """Execute a query on the SADDL database with retry logic for closed connections."""
    pool = get_pool()
    if not pool:
        return []
    
    try:
        with pool.getconn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
            finally:
                pool.putconn(conn)
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"⚠️ SADDL connection lost, resetting pool: {e}")
        global _pool
        if _pool:
            _pool.closeall()
            _pool = None
        # Retry once
        return execute_saddl_query(query, params)
    except Exception as e:
        print(f"[ERROR] SADDL Query Error: {e}")
        return []

def fetch_saddl_accounts():
    """Fetch active accounts from SADDL public.accounts."""
    query = "SELECT account_id, account_name FROM public.accounts ORDER BY account_name"
    rows = execute_saddl_query(query)
    return [{"client_id": r[0], "client_name": r[1]} for r in rows]

def fetch_saddl_categories(account_id):
    """Fetch BSR categories for an account from SADDL sc_raw.bsr_history with product details."""
    query = """
    WITH parent_mapping AS (
        SELECT DISTINCT ON (b.asin)
            b.category_name,
            COALESCE(s.parent_asin, b.asin) as parent_asin,
            b.asin as child_asin,
            b.rank,
            COALESCE(p.title, b.asin) as title
        FROM sc_raw.bsr_history b
        LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
        LEFT JOIN (SELECT DISTINCT ON (asin) asin, title FROM ads.product_catalog) p ON b.asin = p.asin
        WHERE b.account_id = %s
          AND b.report_date >= (CURRENT_DATE - INTERVAL '30 days')
        ORDER BY b.asin, b.report_date DESC
    ),
    category_per_parent AS (
        SELECT DISTINCT ON (parent_asin, category_name)
            parent_asin,
            category_name,
            rank as best_rank,
            title
        FROM parent_mapping
        ORDER BY parent_asin, category_name, rank ASC
    )
    SELECT 
        l.category_name, 
        COUNT(l.parent_asin) as asin_count,
        AVG(l.best_rank) as avg_rank,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'asin', l.parent_asin,
                'rank', l.best_rank,
                'title', l.title
            ) ORDER BY l.best_rank ASC
        ) as products
    FROM category_per_parent l
    GROUP BY l.category_name
    ORDER BY avg_rank ASC;

    """
    rows = execute_saddl_query(query, (account_id,))
    return [
        {
            "category_name": r[0], 
            "asin_count": r[1], 
            "avg_rank": float(r[2]) if r[2] is not None else 0, 
            "products": r[3] or []
        } 
        for r in rows
    ]

def fetch_account_products_with_categories(account_id):
    """Fetch all products for an account with their parent_asin, category_id and name."""
    query = """
    SELECT DISTINCT ON (b.asin)
        b.asin, 
        COALESCE(s.parent_asin, b.asin) as parent_asin,
        b.category_name, 
        b.category_id,
        b.marketplace_id,
        COALESCE(p.title, f.product_name, b.asin) as title
    FROM sc_raw.bsr_history b
    LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
    LEFT JOIN (SELECT DISTINCT ON (asin) asin, title FROM ads.product_catalog) p ON b.asin = p.asin
    LEFT JOIN (SELECT DISTINCT ON (asin) asin, product_name FROM sc_raw.fba_inventory WHERE client_id = %s) f ON b.asin = f.asin
    WHERE b.account_id = %s
      AND b.report_date >= (CURRENT_DATE - INTERVAL '30 days')
    ORDER BY b.asin, b.report_date DESC
    """
    rows = execute_saddl_query(query, (account_id, account_id))
    return [
        {
            "asin": r[0],
            "parent_asin": r[1],
            "category_name": r[2],
            "category_id": r[3],
            "marketplace_id": r[4],
            "title": r[5]
        }
        for r in rows
    ]

def fetch_account_prices(account_id: str) -> dict[str, float]:
    """Fetch selling price for each ASIN, fallback from sales traffic to fba_inventory."""
    # 1. Try Sales Traffic (Recent actual price)
    query_sales = """
        SELECT child_asin, SUM(ordered_revenue) / NULLIF(SUM(units_ordered), 0) as avg_price
        FROM sc_raw.sales_traffic
        WHERE account_id = %s AND units_ordered > 0
        GROUP BY child_asin
    """
    rows_sales = execute_saddl_query(query_sales, (account_id,))
    prices = {r[0]: float(r[1]) for r in rows_sales if r[1] is not None}
    
    # 2. Try FBA Inventory (Catalog price) for missing ones
    query_inv = """
        SELECT DISTINCT ON (asin) asin, your_price
        FROM sc_raw.fba_inventory
        WHERE client_id = %s
        ORDER BY asin, snapshot_date DESC
    """
    rows_inv = execute_saddl_query(query_inv, (account_id,))
    for r in rows_inv:
        if r[0] not in prices and r[1] is not None:
            prices[r[0]] = float(r[1])
            
    return prices

def fetch_account_performance(account_id: str) -> list[dict[str, Any]]:
    """Fetch live performance metrics for each ASIN."""
    query = """
        SELECT 
            t.child_asin as asin,
            t.report_date as performance_date,
            t.units_ordered,
            t.sessions,
            t.ordered_revenue,
            t.unit_session_percentage as cvr,
            a.spend,
            a.sales,
            t.pulled_at as updated_at
        FROM sc_raw.sales_traffic t
        LEFT JOIN ads.product_stats a 
            ON t.child_asin = a.asin 
            AND t.report_date = a.date
            AND a.client_id = %s
        WHERE t.account_id = %s
        AND t.report_date >= (CURRENT_DATE - INTERVAL '30 days')
        ORDER BY t.report_date DESC
    """
    rows = execute_saddl_query(query, (account_id, account_id))
    return [
        {
            "asin": r[0],
            "performance_date": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "units_ordered": int(r[2] or 0),
            "sessions": int(r[3] or 0),
            "revenue": float(r[4] or 0),
            "cvr": float(r[5] or 0),
            "acos": (float(r[6]) / float(r[7]) * 100) if r[7] and float(r[7]) > 0 else 0.0,
            "updated_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8])
        }
        for r in rows
    ]


def fetch_parent_asin_categories(account_id: str, parent_asin: str):
    """Fetch all categories that a parent_asin (and its children) belongs to."""
    query = """
    WITH latest_bsr AS (
        SELECT DISTINCT ON (b.asin)
            b.category_id,
            b.category_name,
            b.marketplace_id
        FROM sc_raw.bsr_history b
        LEFT JOIN sc_raw.sales_traffic s ON b.asin = s.child_asin AND b.account_id = s.account_id
        WHERE b.account_id = %s
          AND (s.parent_asin = %s OR b.asin = %s)
          AND b.report_date >= (CURRENT_DATE - INTERVAL '30 days')
        ORDER BY b.asin, b.report_date DESC
    )
    SELECT DISTINCT category_id, category_name, marketplace_id FROM latest_bsr
    """
    rows = execute_saddl_query(query, (account_id, parent_asin, parent_asin))
    return [
        {
            "category_id": r[0],
            "category_name": r[1],
            "marketplace_id": r[2]
        }
        for r in rows
    ]
