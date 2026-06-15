"""
ScraperGraphAI Provider — Temporary replacement for Apify-based competitor scraping.

This module wraps scrape_competitors.py (copied alongside apify_client.py) and
exposes the same interface expected by discovery_service.trigger_background_discovery().

DO NOT MODIFY scrape_competitors.py itself — this wrapper adapts it.

ROLLBACK: Set SCRAPER_PROVIDER=apify in .env and restart the application.
"""

import os
import sys
import logging
from datetime import date
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import internal functions from scrape_competitors.py (sibling file).
# We import the module-level helpers directly rather than calling main()
# which uses argparse and sys.exit().
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

try:
    # Lazy import so the app can start even if optional deps (psycopg2, requests)
    # are not available during cold startup.
    from scrape_competitors import (  # type: ignore[import]
        load_env,
        get_active_categories,
        scrape_category_with_limit,
        upsert_competitors,
        infer_missing_brands,
        MARKETPLACE_DOMAINS,
    )
    _SCRAPER_MODULE_LOADED = True
    logger.info("scrape_competitors.py Loaded Successfully")
except ImportError as _import_err:
    _SCRAPER_MODULE_LOADED = False
    logger.warning(
        "scrape_competitors.py could not be loaded: %s — "
        "ScraperGraphAI scraping will be unavailable.",
        _import_err,
    )


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------

class ScraperGraphAIProvider:
    """
    Adapter between the application's discovery_service and scrape_competitors.py.

    Usage (called only when a scrape is explicitly requested):
        provider = ScraperGraphAIProvider()
        result   = provider.scrape_all_categories(account_id, db_url)
    """

    def __init__(self):
        logger.info("SCRAPER PROVIDER: scrapergraphai")
        logger.info("Provider Loaded Successfully")
        logger.info("Waiting for Scrape Request")

        self.sgai_key  = os.environ.get("SGAI_API_KEY")
        self.fc_key    = os.environ.get("FIRECRAWL_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

        if not _SCRAPER_MODULE_LOADED:
            logger.warning(
                "ScraperGraphAIProvider instantiated but scrape_competitors module "
                "is not loaded. Calls to scrape_all_categories() will be no-ops."
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_all_categories(
        self,
        account_id: str,
        db_url: str,
        target_count: int = 30,
    ) -> dict:
        """
        Scrape all active BSR categories for the given account using
        ScraperGraphAI (and fallbacks: Crawl4AI, Firecrawl).

        Writes results directly into sc_raw.competitor_pricing — the same
        SADDL table that the downstream analysis pipeline reads from.

        This method is the replacement for the Apify trigger_category_discovery
        call that was previously used inside trigger_background_discovery().

        Args:
            account_id:    The seller/client account ID (e.g. "oneshot_uae").
            db_url:        psycopg2-compatible database connection string.
            target_count:  Minimum number of unique competitor products to
                           extract per category (default: 30, mirrors CLI default).

        Returns:
            dict with keys:
                status          – "completed" | "error" | "no_categories"
                categories_scraped  – number of categories processed
                categories_skipped  – number of categories already scraped today
                errors          – list of error strings
                message         – human-readable summary
        """
        logger.info("Competitor Scraping Requested")
        logger.info("Provider: scrapergraphai")
        logger.info("Executing scrape_competitors.py")

        if not _SCRAPER_MODULE_LOADED:
            msg = "scrape_competitors module not available — ScraperGraphAI scraping skipped."
            logger.error(msg)
            return {"status": "error", "message": msg}

        if not self.sgai_key and not self.fc_key:
            msg = (
                "No ScraperGraphAI/Firecrawl API keys found "
                "(SGAI_API_KEY or FIRECRAWL_API_KEY). Scraping skipped."
            )
            logger.error(msg)
            return {"status": "error", "message": msg}

        today = date.today().strftime("%Y-%m-%d")

        # 1. Fetch active BSR categories from SADDL DB
        active_cats: List[Tuple] = get_active_categories(db_url)
        if not active_cats:
            msg = "No active categories found in sc_raw.bsr_history."
            logger.warning(msg)
            return {"status": "no_categories", "message": msg}

        # 2. Skip categories already scraped today (save API credits)
        scraped_today = self._get_scraped_today(db_url, today)
        logger.info(
            "Found %d active categories; %d already scraped today.",
            len(active_cats), len(scraped_today),
        )

        categories_to_scrape = [
            (m_id, cat_id, cat_name, acc_id)
            for m_id, cat_id, cat_name, acc_id in active_cats
            if cat_id not in scraped_today
        ]

        if not categories_to_scrape:
            msg = "All active categories already scraped today. Nothing to do."
            logger.info(msg)
            return {
                "status": "completed",
                "categories_scraped": 0,
                "categories_skipped": len(active_cats),
                "errors": [],
                "message": msg,
            }

        # 3. Scrape each category and upsert results
        scraped_count = 0
        errors = []

        for m_id, cat_id, cat_name, acc_id in categories_to_scrape:
            domain = MARKETPLACE_DOMAINS.get(m_id)
            if not domain:
                errors.append(f"Unsupported marketplace ID {m_id} for category {cat_id}.")
                logger.warning("Unsupported marketplace ID %s. Skipping category %s.", m_id, cat_id)
                continue

            target_url = f"https://www.amazon.{domain}/gp/bestsellers/goods/{cat_id}"
            logger.info(
                "Scraping category %s (%s) for account %s via ScraperGraphAI: %s",
                cat_id, cat_name or "unknown", acc_id or account_id, target_url,
            )

            try:
                products = scrape_category_with_limit(
                    base_url=target_url,
                    sgai_key=self.sgai_key,
                    fc_key=self.fc_key,
                    domain=domain,
                    target_count=target_count,
                )
                logger.info(
                    "Extracted %d products from category %s.", len(products), cat_id
                )

                # Optional: infer missing brands via OpenAI
                products = infer_missing_brands(products, self.openai_key)

                written = upsert_competitors(
                    db_url=db_url,
                    report_date=today,
                    marketplace_id=m_id,
                    category_id=cat_id,
                    products=products,
                    account_id=acc_id or account_id,
                    category_name=cat_name,
                )
                logger.info(
                    "Upserted %d competitor pricing records for category %s.",
                    written, cat_id,
                )
                scraped_count += 1

            except Exception as exc:
                err_msg = f"Error scraping category {cat_id} ({domain}): {exc}"
                logger.error(err_msg)
                errors.append(err_msg)

        summary = (
            f"ScraperGraphAI scrape complete. "
            f"Scraped {scraped_count} categories, "
            f"skipped {len(scraped_today)} already done today, "
            f"{len(errors)} error(s)."
        )
        logger.info(summary)

        return {
            "status": "completed",
            "categories_scraped": scraped_count,
            "categories_skipped": len(scraped_today),
            "errors": errors,
            "message": summary,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_scraped_today(self, db_url: str, today: str) -> set:
        """Return set of category_ids already scraped today to avoid duplicates."""
        try:
            import psycopg2  # type: ignore[import]
            with psycopg2.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT category_id
                        FROM sc_raw.competitor_pricing
                        WHERE report_date = %s;
                        """,
                        (today,),
                    )
                    return {row[0] for row in cur.fetchall()}
        except Exception as exc:
            logger.warning("Could not query already-scraped categories: %s", exc)
            return set()
