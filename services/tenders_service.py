"""
Tenders and Procurement Service.
Provides query, presentation formatting, and background sync coordination for tenders,
delegating scraping, enrichment, translation, and persistence to services.ingestion.tender_ingestion.
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Any

from alerts.telegram import dispatch_tender_alerts
from alerts.viber import dispatch_viber_bid_alerts
from data.database import get_db, query_bids
from scrapers.tenders import fetch_all_agency_portals, fetch_listing, fetch_notice
from scrapers.translator import is_dhivehi, translate_dhivehi_title
from services.ingestion.tender_ingestion import execute_tender_ingestion

logger = logging.getLogger(__name__)

_LIVE_BIDS_LOCK = threading.Lock()
_LIVE_BIDS_LAST_SYNC: float = 0.0
_LIVE_BIDS_LAST_ATTEMPT: float = 0.0
_LIVE_BIDS_LAST_SUCCESS: float = 0.0
_LIVE_BIDS_IS_SYNCING: bool = False
CACHE_TTL_SECONDS = 300  # 5 minutes

_LIVE_BIDS_SYNC_STATUS: dict[str, Any] = {
    "status": "idle",
    "last_run": None,
    "last_attempt": None,
    "last_success": None,
    "last_error": None,
    "gazette_notices_count": 0,
    "agency_records_count": 0,
    "persisted_count": 0,
    "alerts_dispatched": 0,
}


def get_bids_sync_status() -> dict[str, Any]:
    """Return operational status of the procurement ingestion pipeline."""
    return dict(_LIVE_BIDS_SYNC_STATUS)


def prepare_bids_presentation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize and format bid records with Dhivehi classification and localized titles for UI."""
    from core.time_utils import calculate_minutes_ago, format_relative_time

    for r in rows:
        raw_t = r.get("title", "")
        is_dv = is_dhivehi(raw_t)
        r["is_dhivehi"] = is_dv
        if not r.get("title_en"):
            r["title_en"] = translate_dhivehi_title(raw_t)
        r["title_dv"] = raw_t if is_dv else ""
        pub = r.get("published_date") or r.get("published_iso")
        if pub:
            mins = calculate_minutes_ago(pub)
            r["time_ago"] = format_relative_time(mins, pub)
    return rows


def _run_bids_sync() -> None:
    """Internal worker running in background thread to synchronize Gazette and agency tenders."""
    global _LIVE_BIDS_LAST_SYNC, _LIVE_BIDS_LAST_ATTEMPT, _LIVE_BIDS_LAST_SUCCESS, _LIVE_BIDS_IS_SYNCING
    start_iso = datetime.datetime.now().isoformat()
    _LIVE_BIDS_LAST_ATTEMPT = time.time()
    _LIVE_BIDS_SYNC_STATUS["status"] = "running"
    _LIVE_BIDS_SYNC_STATUS["last_run"] = start_iso
    _LIVE_BIDS_SYNC_STATUS["last_attempt"] = start_iso

    try:
        res = execute_tender_ingestion(
            listing_fetcher=fetch_listing,
            notice_fetcher=fetch_notice,
            agency_fetcher=fetch_all_agency_portals,
            telegram_dispatcher=dispatch_tender_alerts,
            viber_dispatcher=dispatch_viber_bid_alerts,
        )
        errors = res["errors"]
        _LIVE_BIDS_LAST_SUCCESS = time.time()
        _LIVE_BIDS_LAST_SYNC = time.time()
        _LIVE_BIDS_SYNC_STATUS.update({
            "status": "success_with_errors" if errors else "success",
            "last_success": datetime.datetime.now().isoformat(),
            "gazette_notices_count": res["gazette_notices_count"],
            "agency_records_count": res["agency_records_count"],
            "persisted_count": res["persisted_count"],
            "alerts_dispatched": res["alerts_dispatched"],
            "last_error": "; ".join(errors) if errors else None,
        })
    except Exception as exc:
        logger.error("Bids sync critical failure: %s", exc, exc_info=True)
        _LIVE_BIDS_SYNC_STATUS.update({
            "status": "failed",
            "last_error": str(exc),
        })
    finally:
        with _LIVE_BIDS_LOCK:
            _LIVE_BIDS_IS_SYNCING = False


def trigger_bids_background_sync(force: bool = False) -> bool:
    """Trigger background scraping of tenders if not already running and TTL expired."""
    global _LIVE_BIDS_IS_SYNCING, _LIVE_BIDS_LAST_SUCCESS, _LIVE_BIDS_LAST_ATTEMPT
    now = time.time()
    with _LIVE_BIDS_LOCK:
        if _LIVE_BIDS_IS_SYNCING:
            return False
        if not force and _LIVE_BIDS_LAST_ATTEMPT > 0 and (now - _LIVE_BIDS_LAST_ATTEMPT < 30):
            return False
        if not force and _LIVE_BIDS_LAST_SUCCESS > 0 and (now - _LIVE_BIDS_LAST_SUCCESS < CACHE_TTL_SECONDS):
            return False
        _LIVE_BIDS_IS_SYNCING = True
        worker = threading.Thread(target=_run_bids_sync, daemon=True, name="BidsSyncWorker")
        worker.start()
        return True


def get_live_bids(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return persisted tenders from SQLite. Never triggers background scraping on ordinary read."""
    if force_refresh:
        trigger_bids_background_sync(force=True)
    with get_db() as conn:
        return query_bids(conn)
