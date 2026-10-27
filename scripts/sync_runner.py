"""
Standalone Local Scraper & Sync Runner.
Allows local execution of news, tenders, and job scrapers with direct persistence
to target PostgreSQL / Supabase or SQLite database.
Usage:
    python scripts/sync_runner.py --category all
    python scripts/sync_runner.py --category tenders
    python scripts/sync_runner.py --category news
    python scripts/sync_runner.py --category jobs
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.connection import get_db
from data.init_db import init_db
from services.news_service import _run_news_sync, get_live_news
from services.tenders_service import _run_bids_sync, get_bids_sync_status
from scrapers.jobs import sync_jobs
from data.repos.sync_status import get_all_sync_statuses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sync_runner")


def run_sync(category: str) -> None:
    db_target = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or "local sqlite"
    safe_target = "PostgreSQL / Supabase" if "postgres" in db_target else "SQLite"
    logger.info("Initializing sync runner against database: %s", safe_target)
    init_db()

    if category in ("news", "all"):
        logger.info("--- Starting News Synchronization ---")
        try:
            _run_news_sync()
            news = get_live_news(force_refresh=False)
            logger.info("News sync complete: %d clustered stories in memory/database", len(news))
        except Exception as exc:
            logger.error("News sync failed: %s", exc)

    if category in ("tenders", "bids", "all"):
        logger.info("--- Starting Tenders/Bids Synchronization ---")
        try:
            _run_bids_sync()
            status = get_bids_sync_status()
            logger.info(
                "Tenders sync complete: %d gazette, %d agency records, %d persisted",
                status.get("gazette_notices_count", 0),
                status.get("agency_records_count", 0),
                status.get("persisted_count", 0),
            )
        except Exception as exc:
            logger.error("Tenders sync failed: %s", exc)

    if category in ("jobs", "all"):
        logger.info("--- Starting Jobs Synchronization ---")
        try:
            with get_db() as conn:
                res = sync_jobs(conn)
                total = (res.get("new", 0) if isinstance(res, dict) else 0) + (res.get("updated", 0) if isinstance(res, dict) else 0)
                logger.info("Jobs sync complete: %d jobs inserted/updated (fetched %d)", total, res.get("fetched", 0) if isinstance(res, dict) else 0)
        except Exception as exc:
            logger.error("Jobs sync failed: %s", exc)

    if category in ("rentals", "all"):
        logger.info("--- Starting Rentals Synchronization (iBay, Boahiyaa, Hiyaa, Property.mv) ---")
        try:
            from data.scrapers.rentals_scraper import rescrape_and_sync_all_rentals
            from data.rentals import list_rentals
            with get_db() as conn:
                count = rescrape_and_sync_all_rentals(conn)
                r_list = list_rentals(conn)
                logger.info("Rentals sync complete: %d apartment listings in database (scraped %d)", len(r_list), count)
        except Exception as exc:
            logger.error("Rentals sync failed: %s", exc)

    if category in ("obituaries", "all"):
        logger.info("--- Starting Obituaries Synchronization ---")
        try:
            from data.taxonomy import INITIAL_OBITUARIES
            from data.repos.obituaries import upsert_obituary, list_obituaries
            with get_db() as conn:
                for ob in INITIAL_OBITUARIES:
                    upsert_obituary(conn, ob)
                o_list = list_obituaries(conn)
                logger.info("Obituaries sync complete: %d notices in database", len(o_list))
        except Exception as exc:
            logger.error("Obituaries sync failed: %s", exc)

    # Print summary
    logger.info("--- Final Sync Health Table ---")
    try:
        with get_db() as conn:
            statuses = get_all_sync_statuses(conn)
            if statuses:
                for s in statuses:
                    logger.info(
                        "[%s] %s: status=%s, fetched=%d, inserted=%d, http=%s",
                        s.get("category"),
                        s.get("source_id"),
                        s.get("status"),
                        s.get("fetched_count", 0),
                        s.get("inserted_count", 0),
                        s.get("http_status"),
                    )
            else:
                logger.info("No per-source sync logs recorded yet.")
    except Exception as exc:
        logger.warning("Could not read sync status table: %s", exc)


def main():
    parser = argparse.ArgumentParser(description="Khulaasaa Local Sync Runner")
    parser.add_argument(
        "--category",
        choices=["news", "tenders", "bids", "jobs", "rentals", "obituaries", "all"],
        default="all",
        help="Content category to synchronize",
    )
    args = parser.parse_args()
    run_sync(args.category)


if __name__ == "__main__":
    main()
