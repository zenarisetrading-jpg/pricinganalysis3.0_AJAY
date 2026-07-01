"""
Client for reading competitor pricing from sc_raw.competitor_pricing table.
Replaces Apify-based pb_price_events and pb_category_competitors.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

load_dotenv()

SADDL_DATABASE_URL = os.getenv("SADDL_DATABASE_URL")

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        if not SADDL_DATABASE_URL:
            return None
        try:
            _pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, SADDL_DATABASE_URL,
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


def get_latest_competitor_prices(
    marketplace_id: str,
    days_back: int = 2,
    category_ids: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Get latest competitor prices from sc_raw.competitor_pricing.
    Returns dict: asin -> {price, rating, reviews, brand, category_id, category_name, report_date}
    """
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    
    with get_db_connection() as conn:
        if not conn:
            return {}
        cur = conn.cursor()
        try:
            query = """
                SELECT DISTINCT ON (asin) 
                    asin, price_numeric, rating, reviews_count, brand, 
                    category_id, category_name, report_date, title
                FROM sc_raw.competitor_pricing
                WHERE marketplace_id = %s
                AND report_date >= %s
                AND price_numeric IS NOT NULL
                AND price_numeric > 0
            """
            params = [marketplace_id, cutoff]
            
            if category_ids:
                placeholders = ','.join(['%s'] * len(category_ids))
                query += f" AND category_id IN ({placeholders})"
                params.extend(category_ids)
            
            query += " ORDER BY asin, report_date DESC, price_numeric ASC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            result = {}
            for row in rows:
                asin = row[0]
                if asin not in result:
                    result[asin] = {
                        "price": float(row[1]) if row[1] else None,
                        "rating": float(row[2]) if row[2] else None,
                        "reviews": int(row[3]) if row[3] else None,
                        "brand": row[4],
                        "category_id": row[5],
                        "category_name": row[6],
                        "report_date": row[7],
                        "title": row[8]
                    }
            return result
        finally:
            cur.close()


def get_competitors_by_category(
    marketplace_id: str,
    category_id: str,
    report_date: Optional[date] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Get all competitors for a specific category on a specific date.
    """
    if report_date is None:
        report_date = date.today()
    
    with get_db_connection() as conn:
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT asin, title, price_numeric, rating, reviews_count, brand, rank, category_name
                FROM sc_raw.competitor_pricing
                WHERE marketplace_id = %s
                AND category_id = %s
                AND report_date = %s
                AND price_numeric IS NOT NULL
                AND price_numeric > 0
                ORDER BY rank ASC
                LIMIT %s
            """, (marketplace_id, category_id, report_date.isoformat(), limit))
            
            rows = cur.fetchall()
            return [
                {
                    "asin": row[0],
                    "title": row[1],
                    "price": float(row[2]) if row[2] else None,
                    "rating": float(row[3]) if row[3] else None,
                    "reviews": int(row[4]) if row[4] else None,
                    "brand": row[5],
                    "rank": row[6],
                    "category_name": row[7]
                }
                for row in rows
            ]
        finally:
            cur.close()


def get_categories_for_marketplace(marketplace_id: str) -> List[Dict[str, Any]]:
    """Get all distinct categories with competitor data for a marketplace."""
    with get_db_connection() as conn:
        if not conn:
            return []
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT DISTINCT category_id, category_name, COUNT(DISTINCT asin) as competitor_count
                FROM sc_raw.competitor_pricing
                WHERE marketplace_id = %s
                AND category_id IS NOT NULL
                GROUP BY category_id, category_name
                ORDER BY competitor_count DESC
            """, (marketplace_id,))
            rows = cur.fetchall()
            return [
                {"category_id": row[0], "category_name": row[1], "competitor_count": row[2]}
                for row in rows
            ]
        finally:
            cur.close()


def get_latest_report_date(marketplace_id: str) -> Optional[date]:
    """Get the most recent report date for a marketplace."""
    with get_db_connection() as conn:
        if not conn:
            return None
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT MAX(report_date) FROM sc_raw.competitor_pricing
                WHERE marketplace_id = %s
            """, (marketplace_id,))
            row = cur.fetchone()
            return row[0] if row and row[0] else None
        finally:
            cur.close()


MARKETPLACE_MAP = {
    "A2VIGQ35RCS4UG": {"domain": "amazon.ae", "name": "UAE"},
    "A17E79C6D8DWNP": {"domain": "amazon.sa", "name": "KSA"},
}

def get_marketplace_id(marketplace_name: str) -> str:
    """Convert marketplace name (UAE/KSA) to marketplace_id."""
    for mid, info in MARKETPLACE_MAP.items():
        if info["name"] == marketplace_name:
            return mid
    return "A2VIGQ35RCS4UG"  # Default UAE


def get_marketplace_name(marketplace_id: str) -> str:
    """Convert marketplace_id to name (UAE/KSA)."""
    return MARKETPLACE_MAP.get(marketplace_id, {}).get("name", "UAE")