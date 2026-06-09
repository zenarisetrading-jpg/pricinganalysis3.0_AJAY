import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv()


COMPETITOR_COLUMNS = [
    "parent_asin",
    "product_asins",
    "competitor_asin",
    "category_id",
    "competitor_title",
    "competitor_price",
    "rating",
    "reviews",
    "rank",
    "brand",
    "product_url",
    "marketplace",
    "scraped_at",
]


def _connect(env_name: str):
    db_url = os.getenv(env_name)
    if not db_url:
        raise RuntimeError(f"{env_name} is not set")
    return psycopg2.connect(db_url)


def _columns(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table_name,),
    )
    return {row[0] for row in cur.fetchall()}


def _ensure_competitor_schema(cur) -> str:
    cols = _columns(cur, "competitor_products")
    if "parent_asin" not in cols:
        cur.execute("ALTER TABLE public.competitor_products ADD COLUMN parent_asin TEXT")
        if "our_asin" in cols:
            cur.execute("UPDATE public.competitor_products SET parent_asin = our_asin WHERE parent_asin IS NULL")

    cur.execute(
        "ALTER TABLE public.competitor_products ADD COLUMN IF NOT EXISTS product_asins TEXT[] NOT NULL DEFAULT '{}'"
    )

    cols = _columns(cur, "competitor_products")
    if "our_asin" in cols:
        return "our_asin"
    return "parent_asin"


def _fetch_parent_mapping(account_id: str):
    query = """
    SELECT DISTINCT
        b.asin AS child_asin,
        COALESCE(s.parent_asin, b.asin) AS parent_asin,
        b.category_id
    FROM sc_raw.bsr_history b
    LEFT JOIN sc_raw.sales_traffic s
      ON b.asin = s.child_asin
     AND b.account_id = s.account_id
    WHERE b.account_id = %s
      AND b.report_date = (
          SELECT MAX(report_date)
          FROM sc_raw.bsr_history
          WHERE account_id = %s
      )
    """
    with _connect("SADDL_DATABASE_URL") as conn:
        with conn.cursor() as cur:
            cur.execute(query, (account_id, account_id))
            rows = cur.fetchall()

    child_to_parent = {}
    children_by_parent_category = defaultdict(set)
    for child_asin, parent_asin, category_id in rows:
        child_asin = str(child_asin).strip()
        parent_asin = str(parent_asin).strip()
        category_key = str(category_id).strip() if category_id is not None else None
        child_to_parent[child_asin] = parent_asin
        children_by_parent_category[(parent_asin, category_key)].add(child_asin)

    return child_to_parent, children_by_parent_category


def _latest_value(existing, candidate):
    if candidate is not None:
        return candidate
    return existing


def _build_grouped_rows(rows, child_to_parent, children_by_parent_category):
    grouped = {}
    unmapped_sources = set()

    for row in rows:
        (
            source_asin,
            existing_parent_asin,
            existing_product_asins,
            competitor_asin,
            category_id,
            competitor_title,
            competitor_price,
            rating,
            reviews,
            rank,
            brand,
            product_url,
            marketplace,
            scraped_at,
        ) = row

        if not competitor_asin:
            continue

        source_asin = str(source_asin or existing_parent_asin or "").strip()
        category_key = str(category_id).strip() if category_id is not None else None
        parent_asin = child_to_parent.get(source_asin) or str(existing_parent_asin or source_asin).strip()
        if source_asin and source_asin not in child_to_parent and source_asin != parent_asin:
            unmapped_sources.add(source_asin)

        mapped_children = children_by_parent_category.get((parent_asin, category_key), set())
        product_asins = set(mapped_children)
        product_asins.update(existing_product_asins or [])
        if source_asin:
            product_asins.add(source_asin)

        key = (parent_asin, category_key, str(competitor_asin).strip(), marketplace)
        current = grouped.get(key)
        incoming = {
            "parent_asin": parent_asin,
            "product_asins": product_asins,
            "competitor_asin": str(competitor_asin).strip(),
            "category_id": category_key,
            "competitor_title": competitor_title,
            "competitor_price": competitor_price,
            "rating": rating,
            "reviews": reviews,
            "rank": rank,
            "brand": brand,
            "product_url": product_url,
            "marketplace": marketplace,
            "scraped_at": scraped_at,
        }
        if current is None:
            grouped[key] = incoming
            continue

        current["product_asins"].update(product_asins)
        if scraped_at and (current["scraped_at"] is None or scraped_at >= current["scraped_at"]):
            for field in (
                "competitor_title",
                "competitor_price",
                "rating",
                "reviews",
                "rank",
                "brand",
                "product_url",
                "scraped_at",
            ):
                current[field] = _latest_value(current[field], incoming[field])

    output = []
    for item in grouped.values():
        output.append(tuple(
            sorted(item["product_asins"]) if column == "product_asins" else item[column]
            for column in COMPETITOR_COLUMNS
        ))

    return output, unmapped_sources


def group_competitor_products(account_id: str, apply: bool, pricing_env: str):
    child_to_parent, children_by_parent_category = _fetch_parent_mapping(account_id)
    if not child_to_parent:
        raise RuntimeError(f"No SADDL ASIN mapping found for account_id={account_id}")

    with _connect(pricing_env) as conn:
        with conn.cursor() as cur:
            source_column = _ensure_competitor_schema(cur)
            cur.execute(f"""
                SELECT
                    {source_column} AS source_asin,
                    parent_asin,
                    product_asins,
                    competitor_asin,
                    category_id,
                    competitor_title,
                    competitor_price,
                    rating,
                    reviews,
                    rank,
                    brand,
                    product_url,
                    marketplace,
                    scraped_at
                FROM public.competitor_products
            """)
            existing_rows = cur.fetchall()
            grouped_rows, unmapped_sources = _build_grouped_rows(
                existing_rows,
                child_to_parent,
                children_by_parent_category,
            )

            print(f"Existing rows: {len(existing_rows)}")
            print(f"Grouped rows: {len(grouped_rows)}")
            print(f"Mapped child ASINs: {len(child_to_parent)}")
            print(f"Unmapped source ASINs: {len(unmapped_sources)}")

            if not apply:
                conn.rollback()
                print("Dry run only. Re-run with --apply to write changes.")
                return

            backup_name = "competitor_products_backup_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            cur.execute(f"CREATE TABLE public.{backup_name} AS TABLE public.competitor_products")
            cur.execute("TRUNCATE TABLE public.competitor_products RESTART IDENTITY")
            execute_values(
                cur,
                f"""
                INSERT INTO public.competitor_products ({", ".join(COMPETITOR_COLUMNS)})
                VALUES %s
                """,
                grouped_rows,
            )
            cur.execute("ALTER TABLE public.competitor_products ALTER COLUMN parent_asin SET NOT NULL")
            cur.execute("DROP INDEX IF EXISTS public.uq_competitor_products_parent_competitor")
            cur.execute(
                """
                CREATE UNIQUE INDEX uq_competitor_products_parent_competitor
                ON public.competitor_products(parent_asin, category_id, competitor_asin, marketplace)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_competitor_products_parent_category
                ON public.competitor_products(parent_asin, category_id, marketplace)
                """
            )
            conn.commit()
            print(f"Applied grouping. Backup table: public.{backup_name}")


def main():
    parser = argparse.ArgumentParser(description="Group competitor_products by parent ASIN.")
    parser.add_argument("--account-id", required=True, help="SADDL account_id used to resolve child ASINs to parent ASINs.")
    parser.add_argument("--pricing-env", default="PRICING_DATABASE_URL", help="Environment variable for the pricing database URL.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this flag the script only previews counts.")
    args = parser.parse_args()
    group_competitor_products(account_id=args.account_id, apply=args.apply, pricing_env=args.pricing_env)


if __name__ == "__main__":
    main()
