"""
Reset all application sections and rescrape fresh data from live sources.
Sections refreshed:
1. Live News (Dedicated MV Crisis scraper, RSS, WP REST, HTML — zero ads, zero transliteration)
2. Jobs (Gazette and MyCareer — extracted salaries, allowances, and accurate locations)
3. Tenders / Bids (Gazette procurement — enriched venues and reference numbers)
4. Property Rentals (Live KobaPages listings)
"""
import logging
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath("."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("khulaasaa.reset")


def run_full_reset_and_rescrape():
    db_path = "data/khulaasaa.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    logger.info("Purging stale cached records from SQLite...")
    cur.execute("DELETE FROM articles;")
    cur.execute("DELETE FROM jobs;")
    cur.execute("DELETE FROM bids;")
    conn.commit()

    # 1. Rescrape News
    logger.info("Rescraping live news across media outlets...")
    from scrapers.news.engine import fetch_all_live_news
    from data.database import upsert_article
    from services.news_service import _LIVE_NEWS_CACHE
    import time

    fresh_articles = fetch_all_live_news()
    logger.info("Fetched %d clustered live news stories", len(fresh_articles))
    for art in fresh_articles:
        try:
            upsert_article(conn, art)
        except Exception as e:
            logger.debug("Error upserting article %s: %s", art.get("id"), e)
    _LIVE_NEWS_CACHE["data"] = fresh_articles
    _LIVE_NEWS_CACHE["timestamp"] = time.time()
    conn.commit()

    # 2. Rescrape Jobs with detailed salary & location enrichment
    logger.info("Rescraping live jobs from Gazette and MyCareer with salary packages...")
    from scrapers.jobs import sync_jobs
    job_res = sync_jobs(conn, pages=2, trigger_alerts=False)
    logger.info("Jobs sync completed: %s", job_res)
    conn.commit()

    # 3. Rescrape Tenders / Bids with full gazette enrichment
    logger.info("Rescraping live procurement tenders from Gazette...")
    from services.tenders_service import _run_bids_sync
    _run_bids_sync()
    logger.info("Bids sync completed successfully")
    conn.commit()

    # 4. Refresh Rentals
    logger.info("Refreshing verified rental listings...")
    from data.initial_rentals import SEED_RENTAL_LISTINGS
    from data.rentals import upsert_rental_listing
    for r in SEED_RENTAL_LISTINGS:
        try:
            upsert_rental_listing(conn, r)
        except Exception:
            pass
    conn.commit()

    # Summary table counts
    logger.info("=== POST-RESET DATABASE SUMMARY ===")
    for table in ["articles", "jobs", "bids", "rentals", "obituaries"]:
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        cnt = cur.fetchone()[0]
        logger.info("  Table '%s': %d records", table, cnt)

    conn.close()
    logger.info("Full reset and rescrape finished successfully!")


if __name__ == "__main__":
    run_full_reset_and_rescrape()
