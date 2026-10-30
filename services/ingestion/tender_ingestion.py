"""
Tender Ingestion Service.
Coordinates Gazette and agency tender scrapers, enriches notices, translates Dhivehi
titles/agencies/venues, persists to the bids repository, and dispatches alerts.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import os
from typing import Any, Callable, Optional

from alerts.telegram import dispatch_tender_alerts
from alerts.viber import dispatch_viber_bid_alerts
from data.database import get_db, log_db_error, purge_expired_bids, upsert_bid
from scrapers.tenders import (
    BidNotice,
    classify_procurement,
    fetch_all_agency_portals,
    fetch_listing,
    fetch_notice,
)
from scrapers.translator import translate_agency, translate_dhivehi_title, translate_venue

logger = logging.getLogger(__name__)


def resolve_submission_location(
    raw_sub_loc: Optional[str],
    reference_number: Optional[str],
    agency_clean: str,
) -> str:
    """Normalize and translate submission location with sensible agency fallbacks."""
    sub_loc = translate_venue(raw_sub_loc) if raw_sub_loc else None
    if not sub_loc or sub_loc in [
        "This Office",
        "Council Secretariat / Agency Office",
        "Local Council Secretariat",
        "Council Secretariat",
    ]:
        if "13-K" in (reference_number or ""):
            return "National Tender Board, Ministry of Finance, Male'"
        if "HDC" in agency_clean or "Housing Development Corporation" in agency_clean:
            return "HDC Building Reception, Hulhumale'"
        if "Addu City Council" in agency_clean:
            return "Addu City Council Secretariat"
        if "Malé City Council" in agency_clean:
            return "Malé City Council Secretariat"
        if "City Council" in agency_clean or "Council" in agency_clean:
            return f"{agency_clean} Secretariat"
        if "Ministry" in agency_clean:
            return f"{agency_clean}, Male'"
        return f"{agency_clean} Office"
    return sub_loc


def normalize_gazette_notice(n: BidNotice) -> dict[str, Any]:
    """Convert an enriched Gazette BidNotice into a normalized database bid dict."""
    nature, disc = classify_procurement(n.title, getattr(n, "body", None))
    agency_clean = translate_agency(n.agency)
    title_en = translate_dhivehi_title(n.title)
    sub_loc = resolve_submission_location(n.submission_location, n.reference_number, agency_clean)

    info_loc = n.info_location
    if info_loc and not info_loc.startswith("Email:"):
        info_loc = translate_venue(info_loc)

    return {
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


def normalize_agency_record(ar: Any) -> dict[str, Any]:
    """Convert a scraped SOE/Ministry SourceRecord into a normalized database bid dict."""
    nature, disc = classify_procurement(ar.title)
    agency_clean = translate_agency(ar.agency)
    title_en = translate_dhivehi_title(ar.title)
    return {
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


def execute_tender_ingestion(
    listing_fetcher: Callable = fetch_listing,
    notice_fetcher: Callable = fetch_notice,
    agency_fetcher: Callable = fetch_all_agency_portals,
    telegram_dispatcher: Callable = dispatch_tender_alerts,
    viber_dispatcher: Callable = dispatch_viber_bid_alerts,
) -> dict[str, Any]:
    """
    Run full tender ingestion pipeline:
    1. Fetch Gazette listings & enrich uncached notices in parallel.
    2. Fetch SOE & Ministry agency portals.
    3. Normalize, translate, and persist into SQLite.
    4. Dispatch Telegram and Viber alerts.
    """
    errors: list[str] = []
    notices: list[BidNotice] = []
    seen_notice_ids: set[str] = set()
    max_pages = int(os.environ.get("GAZETTE_MAX_PAGES", "3"))

    for page_num in range(1, max_pages + 1):
        try:
            page_items = listing_fetcher(type_slug="beelan", page=page_num)
            if not page_items:
                break
            new_items_count = 0
            for item in page_items:
                if item.notice_id not in seen_notice_ids:
                    seen_notice_ids.add(item.notice_id)
                    notices.append(item)
                    new_items_count += 1
            if new_items_count == 0:
                break
        except Exception as exc:
            logger.warning("Error fetching Gazette listing page %d: %s", page_num, exc)
            errors.append(f"Gazette page {page_num}: {exc}")
            if page_num == 1:
                break

    if notices:
        already_enriched: set[str] = set()
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT notice_id FROM bids WHERE submission_location IS NOT NULL AND reference_number IS NOT NULL;"
                ).fetchall()
                already_enriched = {r[0] for r in rows if r[0]}
        except Exception as exc:
            logger.warning("Failed querying local enriched bids: %s", exc)

        def _enrich_notice(n: BidNotice) -> BidNotice:
            if n.notice_id in already_enriched:
                return n
            if not n.submission_location or not n.reference_number:
                try:
                    detailed = notice_fetcher(n.notice_id)
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

        to_enrich = [n for n in notices if n.notice_id not in already_enriched]
        if to_enrich:
            try:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    list(executor.map(_enrich_notice, to_enrich))
            except Exception as exc:
                logger.warning("Error during parallel notice enrichment: %s", exc)

    new_records = [normalize_gazette_notice(n) for n in notices]

    agency_count = 0
    try:
        agency_records = agency_fetcher()
        agency_count = len(agency_records)
        for ar in agency_records:
            new_records.append(normalize_agency_record(ar))
    except Exception as e:
        logger.warning("Failed to fetch agency portals: %s", e)
        errors.append(f"Agency portals: {e}")

    persisted = 0
    alerts_dispatched = 0
    with get_db() as conn:
        try:
            purge_expired_bids(conn, retention_days=30)
        except Exception as exc:
            logger.warning("Error purging expired bids: %s", exc)

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
                log_db_error(logger, f"upsert_bid_{n_id}", "services.ingestion.tender_ingestion", exc)

        if persisted_records:
            try:
                alert_res = telegram_dispatcher(conn, persisted_records)
                if isinstance(alert_res, dict):
                    alerts_dispatched += alert_res.get("delivered", 0)
            except Exception as exc:
                log_db_error(logger, "dispatch_tender_alerts", "services.ingestion.tender_ingestion", exc)

            try:
                viber_dispatcher(conn, persisted_records)
            except Exception as exc:
                log_db_error(logger, "dispatch_viber_bid_alerts", "services.ingestion.tender_ingestion", exc)

    return {
        "gazette_notices_count": len(notices),
        "agency_records_count": agency_count,
        "persisted_count": persisted,
        "alerts_dispatched": alerts_dispatched,
        "errors": errors,
    }
