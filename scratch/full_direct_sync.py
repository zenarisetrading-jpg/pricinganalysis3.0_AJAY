"""
Full Direct SQL Sync - Properly syncs ALL parent ASINs with real competitor benchmarks.
Uses direct PostgreSQL connection to bypass Supabase RLS issues.
Fetches real prices from sc_raw.sales_traffic.
"""
import os
import psycopg2
import statistics
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Parent ASIN -> child ASINs mapping
PARENT_MAP = {
    "B0FNN5WKDG": ["B0CZLK598D", "B0CZLKLJX5", "B0D39R47CC", "B0F6NHKSQ1", "B0FFB2F46C", "B0FM469PMF", "B0FMYLRD2X", "B0FNN5WKDG"],
    "B0DGLGPN1N": ["B0DGLCG5G1", "B0DGLD7P83", "B0DGLGPN1N", "B0DGLHDFPK"],
    "B0DLX3GJNJ": ["B0DLX3GJNJ"],
    "B0DLX3Y8JN": ["B0DLX3Y8JN"],
    "B0DLX4FKPT": ["B0DLX4FKPT"],
    "B0DLXPQZCJ": ["B0DLXPQZCJ"],
    "B0FM43BSB2": ["B0FM43BSB2"],
    "B0FM45GBTY": ["B0FM45GBTY"],
}

# Known category IDs per parent
PARENT_CATEGORIES = {
    "B0FNN5WKDG":  ["12373047031", "22202768031"],
    "B0DGLGPN1N":  ["22202768031"],
    "B0DLX3GJNJ":  ["12373047031"],
    "B0DLX3Y8JN":  ["12373047031"],
    "B0DLX4FKPT":  ["12373047031"],
    "B0DLXPQZCJ":  ["12373047031"],
    "B0FM43BSB2":  ["12373047031"],
    "B0FM45GBTY":  ["12373047031"],
}

KNOWN_PRICES = {
    "B0DLX4FKPT":  212.0,
    "B0DLXPQZCJ":  320.0,
    "B0FM43BSB2":  55.0,
    "B0FM45GBTY":  45.0,
    "B0FNN5WKDG":  0.0,
    "B0DGLGPN1N":  0.0,
    "B0DLX3GJNJ":  0.0,
    "B0DLX3Y8JN":  0.0,
}

def get_real_prices(saddl_conn):
    """Fetch latest prices from SADDL sales_traffic (ordered_revenue / units_ordered)."""
    cur = saddl_conn.cursor()
    try:
        all_asins = [a for asins in PARENT_MAP.values() for a in asins]
        placeholders = ','.join(['%s'] * len(all_asins))
        
        # Get the most recent non-zero sale for each ASIN
        cur.execute(f"""
            SELECT child_asin, ordered_revenue, units_ordered
            FROM (
                SELECT child_asin, ordered_revenue, units_ordered,
                       ROW_NUMBER() OVER(PARTITION BY child_asin ORDER BY report_date DESC) as rn
                FROM sc_raw.sales_traffic
                WHERE child_asin IN ({placeholders})
                AND ordered_revenue > 0 AND units_ordered > 0
            ) t
            WHERE rn = 1
        """, all_asins)
        
        prices = {}
        for row in cur.fetchall():
            asin = row[0]
            revenue = float(row[1])
            units = int(row[2])
            prices[asin] = round(revenue / units, 2)
            
        return prices
    except Exception as e:
        print(f"Warning: Could not fetch prices from SADDL: {e}")
        return {}
    finally:
        cur.close()

def get_competitor_stats(cur, category_ids, marketplace="UAE"):
    """Get pricing statistics from competitor_products table."""
    placeholders = ','.join(['%s'] * len(category_ids))
    cur.execute(f"""
        SELECT competitor_price
        FROM competitor_products 
        WHERE category_id::text IN ({placeholders})
        AND marketplace = %s
        AND competitor_price IS NOT NULL
        AND competitor_price > 0
    """, [str(c) for c in category_ids] + [marketplace])
    
    prices = sorted([float(r[0]) for r in cur.fetchall()])
    if not prices:
        return None
    
    n = len(prices)
    median = statistics.median(prices)
    p25 = prices[int(n * 0.25)]
    p75 = prices[int(n * 0.75)]
    
    return {
        "n_competitors": n,
        "median": round(median, 2),
        "p25":    round(p25, 2),
        "p75":    round(p75, 2),
        "floor":  round(prices[0], 2),
        "ceiling":round(prices[-1], 2),
    }

def full_sync():
    account_id = "oneshot_uae"
    marketplace = "UAE"
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    pricing_conn = psycopg2.connect(os.getenv("PRICING_DATABASE_URL"))
    pcur = pricing_conn.cursor()
    
    saddl_conn = psycopg2.connect(os.getenv("SADDL_DATABASE_URL"))

    # Fetch real prices from SADDL
    saddl_prices = get_real_prices(saddl_conn)
    print(f"Real prices from SADDL sales_traffic: {saddl_prices}")

    # Merge: saddl_prices override KNOWN_PRICES
    for asin, price in saddl_prices.items():
        if price > 0:
            KNOWN_PRICES[asin] = price

    print(f"Final merged current prices: {KNOWN_PRICES}")

    # Clear old data
    pcur.execute("DELETE FROM pb_recommendations WHERE client_id = %s", (account_id,))
    pcur.execute("DELETE FROM pb_alerts WHERE client_id = %s", (account_id,))
    print(f"Cleared old data for {account_id}.\n")

    inserted = 0

    for parent_asin, child_asins in PARENT_MAP.items():
        print(f"Parent: {parent_asin} ({len(child_asins)} variations)")
        
        cat_ids = PARENT_CATEGORIES.get(parent_asin, ["12373047031"])
        stats = get_competitor_stats(pcur, cat_ids, marketplace)
        
        if not stats:
            print(f"  [WARN] No competitor data found for categories {cat_ids}. Skipping.")
            continue
        
        print(f"  Competitors: {stats['n_competitors']}, P25: {stats['p25']}, Median: {stats['median']}, P75: {stats['p75']}")
        
        # Recommended = mid-market (midpoint of p25 and p75)
        recommended_price = round((stats["p25"] + stats["p75"]) / 2, 2)
        
        for child_asin in child_asins:
            # First check if child has a specific price, otherwise fallback to parent price
            current_price = KNOWN_PRICES.get(child_asin)
            if current_price is None or current_price == 0.0:
                current_price = KNOWN_PRICES.get(parent_asin, 0.0)
            
            if current_price > 0:
                # Calculate change percentage
                change_amount = recommended_price - current_price
                change_pct = (change_amount / current_price) * 100
                
                if abs(change_pct) < 1.0:
                    action = "hold"
                elif change_amount > 0:
                    action = "increase"
                else:
                    action = "decrease"
                
                # Zone calculation
                if current_price > stats["p75"]:
                    zone = "premium"
                elif current_price < stats["p25"]:
                    zone = "budget"
                else:
                    zone = "mid"
            else:
                action, zone = "decrease", "unknown"
            
            reasoning = (
                f"{stats['n_competitors']} competitors. "
                f"Range AED{stats['floor']:.2f}-AED{stats['ceiling']:.2f}. "
                f"Median AED{stats['median']:.2f}. | "
                f"Currently in {zone} zone. | "
                f"Mid-market strategy: midpoint of p25 (AED{stats['p25']:.2f}) "
                f"and p75 (AED{stats['p75']:.2f}). "
                f"Median: AED{stats['median']:.2f}."
            )
            
            pcur.execute("""
                INSERT INTO pb_recommendations (
                    client_id, asin, parent_asin, sku_id, marketplace,
                    strategy, current_price, recommended_price, action,
                    reasoning, confidence, status, snapshot_date, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                account_id, child_asin, parent_asin, child_asin, marketplace,
                "mid", current_price, recommended_price, action,
                reasoning, "high", "pending", today, now
            ))
            inserted += 1
        
        # Update daily snapshot for parent
        parent_price = KNOWN_PRICES.get(parent_asin, 0.0)
        pcur.execute("""
            INSERT INTO pb_client_snapshots_daily (
                client_id, sku_id, asin, parent_asin, snapshot_date,
                your_price, n_competitors, floor_price, ceiling_price,
                median_price, p25_price, p75_price, zone, strategy
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (client_id, asin, snapshot_date) DO UPDATE SET
                your_price       = EXCLUDED.your_price,
                n_competitors    = EXCLUDED.n_competitors,
                floor_price      = EXCLUDED.floor_price,
                ceiling_price    = EXCLUDED.ceiling_price,
                median_price     = EXCLUDED.median_price,
                p25_price        = EXCLUDED.p25_price,
                p75_price        = EXCLUDED.p75_price,
                zone             = EXCLUDED.zone
        """, (
            account_id, parent_asin, parent_asin, parent_asin, today,
            parent_price, stats["n_competitors"],
            stats["floor"], stats["ceiling"],
            stats["median"], stats["p25"], stats["p75"],
            zone, "mid"
        ))
        print(f"  [OK] Inserted {len(child_asins)} recommendations. Recommended price: AED{recommended_price}")

    pricing_conn.commit()
    print(f"\nDONE. Total records inserted: {inserted}")
    pcur.close()
    pricing_conn.close()
    saddl_conn.close()

if __name__ == "__main__":
    full_sync()
