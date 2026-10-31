"""
Rentals Ingestion Service.
Coordinates rental portal scrapers, cross-portal consolidation, and non-destructive
database persistence via data.repos.rentals.
"""
from __future__ import annotations

import datetime
import logging
import sqlite3
from typing import Any, Optional

from data.database import get_db
from data.repos.rentals import upsert_rental_listing
from scrapers.rentals.engine import fetch_and_consolidate_rentals

logger = logging.getLogger(__name__)

_RENTALS_SYNC_STATUS: dict[str, Any] = {
    "status": "idle",
    "last_run": None,
    "last_success": None,
    "last_error": None,
    "synced_count": 0,
    "sources_attempted": 0,
}


def get_rentals_sync_status() -> dict[str, Any]:
    """Return operational status and metadata of the rental ingestion pipeline."""
    return dict(_RENTALS_SYNC_STATUS)


def _sync_with_conn(conn: sqlite3.Connection, sources: Optional[list] = None) -> int:
    start_iso = datetime.datetime.now().isoformat()
    _RENTALS_SYNC_STATUS["status"] = "running"
    _RENTALS_SYNC_STATUS["last_run"] = start_iso

    all_scraped, errors, attempted = fetch_and_consolidate_rentals(sources=sources)
    _RENTALS_SYNC_STATUS["sources_attempted"] = attempted

    synced_count = 0
    updated_count = 0
    try:
        conn.execute("SAVEPOINT rentals_sync_sp;")
        for item in all_scraped:
            try:
                created, _ = upsert_rental_listing(conn, item)
                if created:
                    synced_count += 1
                else:
                    updated_count += 1
            except Exception as exc:
                logger.warning("Failed to upsert rental listing: %s", exc)
        conn.execute("RELEASE SAVEPOINT rentals_sync_sp;")
        conn.commit()

        _RENTALS_SYNC_STATUS.update({
            "status": "success_with_errors" if errors else "success",
            "last_success": datetime.datetime.now().isoformat(),
            "synced_count": synced_count + updated_count,
            "last_error": "; ".join(errors) if errors else None,
        })
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT rentals_sync_sp;")
        except Exception:
            pass
        logger.error("Rental sync transaction aborted: %s", exc, exc_info=True)
        _RENTALS_SYNC_STATUS.update({"status": "failed", "last_error": str(exc)})

    logger.info("Rental sync complete: %d inserted, %d updated.", synced_count, updated_count)
    return synced_count + updated_count


def rescrape_and_sync_all_rentals(
    conn: Optional[sqlite3.Connection] = None,
    sources: Optional[list] = None,
) -> int:
    """
    Safely synchronizes rental listings across Maldivian property platforms.
    Guarantees:
    1. NEVER executes broad DELETE FROM rentals WHERE is_direct = 0.
    2. A failed source preserves all existing listings.
    3. Direct submissions are completely untouched.
    4. Upserts by stable canonical source_url.
    """
    if conn is not None:
        return _sync_with_conn(conn, sources=sources)

    with get_db() as db_conn:
        return _sync_with_conn(db_conn, sources=sources)
