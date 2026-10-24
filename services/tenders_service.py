"""
Tenders and Procurement Synchronization Service.
Orchestrates background polling of Gazette, SOEs, and state ministries, applies translations,
stores into database, and triggers subscriber alerts.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from data.database import get_db, purge_expired_bids, query_bids, upsert_bid
from scrapers.agencies import fetch_all_agency_portals
from scrapers.gazette import classify_procurement, fetch_listing, fetch_notice
from scrapers.translator import translate_agency, translate_dhivehi_title, translate_venue
from alerts.telegram import dispatch_tender_alerts

logger = logging.getLogger(__name__)

_LIVE_BIDS_LOCK = threading.Lock()
_LIVE_BIDS_LAST_SYNC: float = 0.0
_LIVE_BIDS_IS_SYNCING: bool = False
CACHE_TTL_SECONDS = 300  # 5 minutes


def _run_bids_sync() -> None:
    """Internal worker running in background thread to fetch Gazette and agency tenders."""
    global _LIVE_BIDS_IS_SYNCING, _LIVE_BIDS_LAST_SYNC
    try:
        # 1. Fetch listings and enrich notices over HTTP (NO DB connection held)
        notices = []
        try:
            notices = fetch_listing(type_slug="beelan", page=1)
            try:
                notices += fetch_listing(type_slug="beelan", page=2)
            except Exception:
                pass
        except Exception:
            pass

        if notices:
            def _enrich_notice(n):
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
                    except Exception:
                        pass
                return n

            try:
                with ThreadPoolExecutor(max_workers=6) as executor:
                    notices = list(executor.map(_enrich_notice, notices))
            except Exception:
                pass

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
        try:
            agency_records = fetch_all_agency_portals()
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

        # 3. Store into DB in a fast atomic transaction
        with get_db() as conn:
            try:
                purge_expired_bids(conn, retention_days=30)
            except Exception:
                pass

            for bid_dict in new_records:
                try:
                    upsert_bid(conn, bid_dict)
                except Exception:
                    pass

            try:
                dispatch_tender_alerts(conn, new_records)
            except Exception:
                pass
    finally:
        _LIVE_BIDS_LAST_SYNC = time.time()
        _LIVE_BIDS_IS_SYNCING = False


def trigger_bids_background_sync(force: bool = False) -> bool:
    """Trigger background scraping of tenders if not already running and TTL expired."""
    global _LIVE_BIDS_IS_SYNCING, _LIVE_BIDS_LAST_SYNC
    now = time.time()
    with _LIVE_BIDS_LOCK:
        if _LIVE_BIDS_IS_SYNCING:
            return False
        if not force and _LIVE_BIDS_LAST_SYNC > 0 and (now - _LIVE_BIDS_LAST_SYNC < CACHE_TTL_SECONDS):
            return False
        _LIVE_BIDS_IS_SYNCING = True
        worker = threading.Thread(target=_run_bids_sync, daemon=True)
        worker.start()
        return True


def get_live_bids(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Ensures background sync is scheduled and returns DB bids instantly."""
    trigger_bids_background_sync(force=force_refresh)
    with get_db() as conn:
        return query_bids(conn)
