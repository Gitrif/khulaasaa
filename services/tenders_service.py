"""
Tenders and Procurement Synchronization Service.
Orchestrates background polling of Gazette, SOEs, and state ministries, applies translations,
stores into database, and triggers subscriber alerts.
"""
from __future__ import annotations

import datetime
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from data.database import get_db, purge_expired_bids, query_bids, upsert_bid
from scrapers.agencies import fetch_all_agency_portals
from scrapers.gazette import classify_procurement, fetch_listing, fetch_notice
from scrapers.translator import is_dhivehi, translate_agency, translate_dhivehi_title, translate_venue
from alerts.telegram import dispatch_tender_alerts
from alerts.viber import dispatch_viber_bid_alerts

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
        if is_dv:
            r["title_dv"] = raw_t
        else:
            r["title_dv"] = ""
        pub = r.get("published_date") or r.get("published_iso")
        if pub:
            mins = calculate_minutes_ago(pub)
            r["time_ago"] = format_relative_time(mins, pub)
    return rows


def _run_bids_sync() -> None:
    """Internal worker running in background thread to fetch Gazette and agency tenders."""
    global _LIVE_JOBS_IS_SYNCING, _LIVE_BIDS_LAST_SYNC, _LIVE_BIDS_LAST_ATTEMPT, _LIVE_BIDS_LAST_SUCCESS, _LIVE_BIDS_IS_SYNCING
    start_iso = datetime.datetime.now().isoformat()
    _LIVE_BIDS_LAST_ATTEMPT = time.time()
    _LIVE_BIDS_SYNC_STATUS["status"] = "running"
    _LIVE_BIDS_SYNC_STATUS["last_run"] = start_iso
    _LIVE_BIDS_SYNC_STATUS["last_attempt"] = start_iso
    errors: list[str] = []

    try:
        # 1. Fetch Gazette listings with robust pagination and cycle detection
        notices = []
        seen_notice_ids = set()
        max_pages = int(os.environ.get("GAZETTE_MAX_PAGES", "3"))

        for page_num in range(1, max_pages + 1):
            try:
                page_items = fetch_listing(type_slug="beelan", page=page_num)
                if not page_items:
                    break
                new_items_count = 0
                for item in page_items:
                    if item.notice_id not in seen_notice_ids:
                        seen_notice_ids.add(item.notice_id)
                        notices.append(item)
                        new_items_count += 1
                if new_items_count == 0:
                    # Repeated page detected (reached end of pagination)
                    break
            except Exception as exc:
                logger.warning("Error fetching Gazette listing page %d: %s", page_num, exc)
                errors.append(f"Gazette page {page_num}: {exc}")
                if page_num == 1:
                    break

        _LIVE_BIDS_SYNC_STATUS["gazette_notices_count"] = len(notices)

        if notices:
            # Query local DB for already enriched notices to avoid redundant external HTTP requests
            already_enriched: set[str] = set()
            try:
                with get_db() as conn:
                    rows = conn.execute(
                        "SELECT notice_id FROM bids WHERE submission_location IS NOT NULL AND reference_number IS NOT NULL;"
                    ).fetchall()
                    already_enriched = {r[0] for r in rows if r[0]}
            except Exception as exc:
                logger.warning("Failed querying local enriched bids: %s", exc)

            def _enrich_notice(n):
                # Skip external HTTP request if this notice was already enriched in database
                if n.notice_id in already_enriched:
                    return n
                if not n.submission_location or not n.reference_number:
                    try:
                        detailed = fetch_notice(n.notice_id)
                        if detailed.reference_number:
                            n.reference_number = detailed.reference_number
                        if detailed.submission_location:
                            n.submission_location = detailed.submission_location
                        if detailed.info_date:
                            n.info_date = detailed.info_date
                        if detailed.info_location:
                            n.info_location = detailed.info_location
                        if detailed.document_urls:
                            n.document_urls = detailed.document_urls
                        if detailed.body:
                            n.body = detailed.body
                        if detailed.deadline_iso:
                            n.deadline_iso = detailed.deadline_iso
                    except Exception as err:
                        logger.debug("Notice %s detail enrichment skipped: %s", n.notice_id, err)
                return n

            # Only run thread pool if there are notices that actually need network enrichment
            to_enrich = [n for n in notices if n.notice_id not in already_enriched]
            if to_enrich:
                try:
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        list(executor.map(_enrich_notice, to_enrich))
                except Exception as exc:
                    logger.warning("Error during parallel notice enrichment: %s", exc)

        new_records = []
        for n in notices:
            nature, disc = classify_procurement(n.title, getattr(n, "body", None))
            agency_clean = translate_agency(n.agency)
            title_en = translate_dhivehi_title(n.title)

            sub_loc = n.submission_location
            if sub_loc:
                sub_loc = translate_venue(sub_loc)
            if not sub_loc or sub_loc in [
                "This Office",
                "Council Secretariat / Agency Office",
                "Local Council Secretariat",
                "Council Secretariat",
            ]:
                if "13-K" in (n.reference_number or ""):
                    sub_loc = "National Tender Board, Ministry of Finance, Male'"
                elif "HDC" in agency_clean or "Housing Development Corporation" in agency_clean:
                    sub_loc = "HDC Building Reception, Hulhumale'"
                elif "Addu City Council" in agency_clean:
                    sub_loc = "Addu City Council Secretariat"
                elif "Malé City Council" in agency_clean:
                    sub_loc = "Malé City Council Secretariat"
                elif "City Council" in agency_clean:
                    sub_loc = f"{agency_clean} Secretariat"
                elif "Council" in agency_clean:
                    sub_loc = f"{agency_clean} Secretariat"
                elif "Ministry" in agency_clean:
                    sub_loc = f"{agency_clean}, Male'"
                else:
                    sub_loc = f"{agency_clean} Office"

            info_loc = n.info_location
            if info_loc and not info_loc.startswith("Email:"):
                info_loc = translate_venue(info_loc)

            bid_dict = {
                "notice_id": n.notice_id,
                "ref": n.reference_number or None,
                "reference_number": n.reference_number or None,
                "agency": agency_clean,
                "agency_raw": n.agency,
                "title": n.title,
                "title_en": title_en,
                "discipline": disc,
                "procurement_nature": nature,
                "gazette_type": n.gazette_type or "Bid",
                "published_date": n.published_iso,
                "published_iso": n.published_iso,
                "submission_date": n.deadline_iso,
                "deadline_iso": n.deadline_iso,
                "submission_location": sub_loc,
                "info_date": n.info_date,
                "info_location": info_loc,
                "source_url": n.url,
                "sources": ["gazette.gov.mv"],
                "document_urls": getattr(n, "document_urls", []),
                "raw_details": getattr(n, "body", None),
            }
            new_records.append(bid_dict)

        # 2. Poll SOE and Ministry tender pages
        agency_count = 0
        try:
            agency_records = fetch_all_agency_portals()
            agency_count = len(agency_records)
            for ar in agency_records:
                nature, disc = classify_procurement(ar.title)
                agency_clean = translate_agency(ar.agency)
                title_en = translate_dhivehi_title(ar.title)
                agency_bid = {
                    "notice_id": f"{ar.source_name}-{ar.reference_number or hash(ar.title)}",
                    "ref": ar.reference_number,
                    "reference_number": ar.reference_number,
                    "agency": agency_clean,
                    "title": ar.title,
                    "title_en": title_en,
                    "discipline": disc,
                    "procurement_nature": nature,
                    "gazette_type": "Bid",
                    "published_date": ar.published_iso,
                    "submission_date": ar.deadline_iso,
                    "submission_location": ar.submission_location,
                    "info_date": ar.info_date,
                    "info_location": ar.info_location,
                    "source_url": ar.source_url,
                    "sources": [ar.source_name],
                    "document_urls": ar.document_urls,
                }
                new_records.append(agency_bid)
        except Exception as e:
            logger.warning("Failed to fetch agency portals: %s", e)
            errors.append(f"Agency portals: {e}")

        _LIVE_BIDS_SYNC_STATUS["agency_records_count"] = agency_count

        # 3. Store into DB in a fast atomic transaction
        persisted = 0
        with get_db() as conn:
            try:
                purge_expired_bids(conn, retention_days=30)
            except Exception as exc:
                logger.warning("Error purging expired bids: %s", exc)

            from data.database import log_db_error
            persisted_records = []
            for bid_dict in new_records:
                n_id = bid_dict.get("notice_id")
                try:
                    conn.execute("SAVEPOINT bid_savepoint;")
                    upsert_bid(conn, bid_dict)
                    conn.execute("RELEASE SAVEPOINT bid_savepoint;")
                    persisted += 1
                    persisted_records.append(bid_dict)
                except Exception as exc:
                    try:
                        conn.execute("ROLLBACK TO SAVEPOINT bid_savepoint;")
                    except Exception:
                        pass
                    log_db_error(logger, f"upsert_bid_{n_id}", "services.tenders_service", exc)

            alerts_dispatched = 0
            if persisted_records:
                try:
                    alert_res = dispatch_tender_alerts(conn, persisted_records)
                    if isinstance(alert_res, dict):
                        alerts_dispatched += alert_res.get("delivered", 0)
                except Exception as exc:
                    log_db_error(logger, "dispatch_tender_alerts", "services.tenders_service", exc)

                try:
                    dispatch_viber_bid_alerts(conn, persisted_records)
                except Exception as exc:
                    log_db_error(logger, "dispatch_viber_bid_alerts", "services.tenders_service", exc)

        _LIVE_BIDS_LAST_SUCCESS = time.time()
        _LIVE_BIDS_LAST_SYNC = time.time()
        _LIVE_BIDS_SYNC_STATUS.update({
            "status": "success_with_errors" if errors else "success",
            "last_success": datetime.datetime.now().isoformat(),
            "persisted_count": persisted,
            "alerts_dispatched": alerts_dispatched,
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
