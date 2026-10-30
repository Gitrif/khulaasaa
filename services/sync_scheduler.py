"""
Periodic Background Sync Scheduler.
Coordinates background synchronization of News, Tenders, Jobs, and Rentals
without coupling scraper orchestration to the FastAPI application entry point.
"""
from __future__ import annotations

import logging
import os
import threading
import time

from services.ingestion.rentals_ingestion import rescrape_and_sync_all_rentals
from services.jobs_service import trigger_jobs_background_sync
from services.news_service import get_live_news
from services.tenders_service import trigger_bids_background_sync

logger = logging.getLogger("khulaasaa.scheduler")

_SHUTDOWN_EVENT = threading.Event()


def _periodic_sync_worker() -> None:
    """Background worker that periodically syncs news, tenders, jobs, and rentals with graceful shutdown."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if _SHUTDOWN_EVENT.wait(timeout=10):
        return

    iteration = 0
    while not _SHUTDOWN_EVENT.is_set():
        iteration += 1

        # News sync every iteration (approx every 3 mins)
        t0 = time.time()
        try:
            get_live_news(force_refresh=True)
            logger.info("Periodic coordinator: news sync scheduled (took %.2fs)", time.time() - t0)
        except Exception as exc:
            logger.warning("Periodic coordinator news sync failed: %s", exc)

        # Tenders sync every 2 iterations (approx every 6 mins)
        if iteration % 2 == 0:
            t0 = time.time()
            try:
                trigger_bids_background_sync(force=True)
                logger.info("Periodic coordinator: tenders sync scheduled (took %.2fs)", time.time() - t0)
            except Exception as exc:
                logger.warning("Periodic coordinator tenders sync failed: %s", exc)

        # Jobs sync on first run and every 5 iterations (approx every 15 mins)
        if iteration == 1 or iteration % 5 == 0:
            t0 = time.time()
            try:
                trigger_jobs_background_sync(force=True)
                logger.info("Periodic coordinator: jobs sync scheduled (took %.2fs)", time.time() - t0)
            except Exception as exc:
                logger.warning("Periodic coordinator jobs sync failed: %s", exc)

        # Rentals sync on first run and every 20 iterations (approx every 60 mins)
        if iteration == 1 or iteration % 20 == 0:
            t0 = time.time()
            try:
                cnt = rescrape_and_sync_all_rentals()
                logger.info(
                    "Periodic coordinator: rentals sync completed, %d records synced (took %.2fs)",
                    cnt,
                    time.time() - t0,
                )
            except Exception as exc:
                logger.warning("Periodic coordinator rentals sync failed: %s", exc)

        if _SHUTDOWN_EVENT.wait(timeout=180):
            break


def start_sync_scheduler() -> None:
    """Start startup triggers and the periodic synchronization worker thread."""
    _SHUTDOWN_EVENT.clear()
    trigger_bids_background_sync(force=False)
    threading.Thread(
        target=lambda: (time.sleep(3), trigger_jobs_background_sync(force=False)),
        daemon=True,
        name="StartupJobsTrigger",
    ).start()
    threading.Thread(
        target=_periodic_sync_worker,
        daemon=True,
        name="PeriodicSyncCoordinator",
    ).start()


def stop_sync_scheduler() -> None:
    """Signal the periodic synchronization worker to stop gracefully."""
    _SHUTDOWN_EVENT.set()
