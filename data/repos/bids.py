"""
Bids and Tenders Repository.
Encapsulates all database operations, filters, statistics, and purging for procurement notices.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional
from data.repos.entities import resolve_or_create_entity

logger = logging.getLogger(__name__)

def upsert_bid(conn: sqlite3.Connection, bid: dict[str, Any]) -> int:
    """Insert or update a tender notice in the database."""
    # Resolve entity ID
    agency_name = bid.get("agency") or "Unknown Agency"
    entity_id = bid.get("entity_id")
    if not entity_id:
        entity_id = resolve_or_create_entity(conn, agency_name)

    # Format document URLs as JSON
    doc_urls = bid.get("document_urls") or []
    if isinstance(doc_urls, list):
        doc_urls_json = json.dumps(doc_urls)
    else:
        doc_urls_json = json.dumps([str(doc_urls)])

    title = bid["title"]
    title_en = bid.get("title_en")
    if not title_en:
        from scrapers.translator import translate_dhivehi_title
        title_en = translate_dhivehi_title(title)

    sub_loc = bid.get("submission_location")
    if sub_loc:
        from scrapers.translator import is_dhivehi, translate_venue
        if is_dhivehi(sub_loc):
            sub_loc = translate_venue(sub_loc)

    info_loc = bid.get("info_location")
    if info_loc and not str(info_loc).startswith("Email:"):
        from scrapers.translator import is_dhivehi, translate_venue
        if is_dhivehi(str(info_loc)):
            info_loc = translate_venue(str(info_loc))

    ref_raw = bid.get("reference_number") or bid.get("ref")
    new_sources = bid.get("sources")
    if not new_sources:
        s_single = bid.get("source_name") or bid.get("source") or "gazette.gov.mv"
        new_sources = [s_single] if isinstance(s_single, str) else list(s_single)

    # Cross-source repetition matching: check if reference number exists across portals
    existing_row = None
    if ref_raw:
        from scrapers.dedupe import normalize_reference
        norm_ref = normalize_reference(ref_raw)
        rows_with_ref = conn.execute(
            "SELECT id, notice_id, reference_number, sources, document_urls, submission_date, submission_location, info_date, info_location FROM bids WHERE reference_number IS NOT NULL;"
        ).fetchall()
        for r in rows_with_ref:
            if r["reference_number"] and normalize_reference(r["reference_number"]) == norm_ref:
                existing_row = r
                break

    # Fallback repetition matching: match same entity + normalized title
    if not existing_row and entity_id:
        from scrapers.dedupe import normalize_title
        curr_t_norm = normalize_title(title_en or title)
        if len(curr_t_norm) > 12:
            entity_rows = conn.execute(
                "SELECT id, notice_id, title, title_en, reference_number, sources, document_urls, submission_date, submission_location, info_date, info_location FROM bids WHERE entity_id = ?;",
                (entity_id,),
            ).fetchall()
            for r in entity_rows:
                db_t_norm = normalize_title(r["title_en"] or r["title"])
                if db_t_norm == curr_t_norm or (len(curr_t_norm) >= 20 and (curr_t_norm in db_t_norm or db_t_norm in curr_t_norm)):
                    existing_row = r
                    break

    if existing_row:
        try:
            curr_sources = json.loads(existing_row["sources"]) if existing_row["sources"] else []
        except Exception:
            curr_sources = ["gazette.gov.mv"]
        merged_sources = sorted(list(set(curr_sources + new_sources)))

        try:
            curr_docs = json.loads(existing_row["document_urls"]) if existing_row["document_urls"] else []
        except Exception:
            curr_docs = []
        new_docs = bid.get("document_urls") or []
        if isinstance(new_docs, str):
            new_docs = [new_docs]
        merged_docs = sorted(list(set(curr_docs + new_docs)))

        conn.execute(
            """
            UPDATE bids SET
                reference_number = COALESCE(bids.reference_number, :reference_number),
                sources = :sources,
                document_urls = :document_urls,
                submission_date = COALESCE(:submission_date, bids.submission_date),
                submission_location = COALESCE(:submission_location, bids.submission_location),
                info_date = COALESCE(:info_date, bids.info_date),
                info_location = COALESCE(:info_location, bids.info_location),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id;
            """,
            {
                "id": existing_row["id"],
                "reference_number": ref_raw,
                "sources": json.dumps(merged_sources),
                "document_urls": json.dumps(merged_docs),
                "submission_date": bid.get("submission_date") or bid.get("deadline_iso"),
                "submission_location": sub_loc,
                "info_date": bid.get("info_date"),
                "info_location": info_loc,
            },
        )
        return existing_row["id"]

    nature = bid.get("procurement_nature")
    if not nature:
        from scrapers.tenders.classifier import classify_procurement
        nature, _ = classify_procurement(title, bid.get("raw_details") or bid.get("body"))

    # Normalize source URL so it always points to the actual tender notice
    raw_src = bid.get("source_url") or ""
    n_id_str = str(bid.get("notice_id") or "")
    if raw_src.startswith("/"):
        raw_src = f"https://gazette.gov.mv{raw_src}"
    elif n_id_str.isdigit() and (not raw_src or raw_src == "https://gazette.gov.mv/iulaan" or "/print/" in raw_src):
        raw_src = f"https://gazette.gov.mv/iulaan/{n_id_str}"
    elif not raw_src and n_id_str.isdigit():
        raw_src = f"https://gazette.gov.mv/iulaan/{n_id_str}"

    from data.repos.sources import resolve_or_create_source
    s_ident = (new_sources[0] if new_sources else None) or bid.get("source_url") or "gazette"
    source_id = bid.get("source_id")
    if not source_id or int(source_id) <= 0:
        source_id = resolve_or_create_source(
            conn, s_ident, source_type="official" if "gazette" in str(s_ident) else "portal"
        )

    from core.time_utils import parse_datetime_components
    pub_raw_val = bid.get("published_date") or bid.get("published_iso")
    pub_at, post_d, post_t = parse_datetime_components(pub_raw_val)
    sub_raw_val = bid.get("submission_date") or bid.get("deadline_iso")
    sub_at, _, _ = parse_datetime_components(sub_raw_val) if sub_raw_val else (None, None, None)

    cursor = conn.execute(
        """
        INSERT INTO bids (
            notice_id, source_id, entity_id, reference_number, title, title_en, gazette_type,
            discipline, procurement_nature, published_date, posted_date, posted_time, published_at,
            submission_date, submission_deadline, submission_location,
            info_date, info_location, source_url, sources, document_urls, raw_details,
            updated_at
        ) VALUES (
            :notice_id, :source_id, :entity_id, :reference_number, :title, :title_en, :gazette_type,
            :discipline, :procurement_nature, :published_date, :posted_date, :posted_time, :published_at,
            :submission_date, :submission_deadline, :submission_location,
            :info_date, :info_location, :source_url, :sources, :document_urls, :raw_details,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(notice_id) DO UPDATE SET
            source_id = COALESCE(excluded.source_id, bids.source_id),
            entity_id = excluded.entity_id,
            reference_number = COALESCE(excluded.reference_number, bids.reference_number),
            title = excluded.title,
            title_en = COALESCE(excluded.title_en, bids.title_en),
            gazette_type = excluded.gazette_type,
            discipline = excluded.discipline,
            procurement_nature = excluded.procurement_nature,
            published_date = COALESCE(excluded.published_date, bids.published_date),
            posted_date = COALESCE(excluded.posted_date, bids.posted_date),
            posted_time = COALESCE(excluded.posted_time, bids.posted_time),
            published_at = COALESCE(excluded.published_at, bids.published_at),
            submission_date = COALESCE(excluded.submission_date, bids.submission_date),
            submission_deadline = COALESCE(excluded.submission_deadline, bids.submission_deadline),
            submission_location = COALESCE(excluded.submission_location, bids.submission_location),
            info_date = COALESCE(excluded.info_date, bids.info_date),
            info_location = COALESCE(excluded.info_location, bids.info_location),
            source_url = CASE WHEN excluded.source_url != '' AND excluded.source_url != 'https://gazette.gov.mv/iulaan' THEN excluded.source_url ELSE bids.source_url END,
            sources = excluded.sources,
            document_urls = excluded.document_urls,
            raw_details = COALESCE(excluded.raw_details, bids.raw_details),
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """,
        {
            "notice_id": str(bid["notice_id"]),
            "source_id": source_id,
            "entity_id": entity_id,
            "reference_number": ref_raw,
            "title": title,
            "title_en": title_en,
            "gazette_type": bid.get("gazette_type", "Bid"),
            "discipline": bid.get("discipline", "Other"),
            "procurement_nature": nature or "Supply",
            "published_date": pub_raw_val,
            "posted_date": post_d,
            "posted_time": post_t,
            "published_at": pub_at,
            "submission_date": sub_raw_val,
            "submission_deadline": sub_at,
            "submission_location": sub_loc,
            "info_date": bid.get("info_date"),
            "info_location": info_loc,
            "source_url": raw_src,
            "sources": json.dumps(new_sources),
            "document_urls": doc_urls_json,
            "raw_details": bid.get("raw_details") or bid.get("body"),
        },
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def query_bids(
    conn: sqlite3.Connection,
    agency_name: Optional[str] = None,
    entity_slug: Optional[str] = None,
    entity_type: Optional[str] = None,
    discipline: Optional[str] = None,
    procurement_nature: Optional[str] = None,
    gazette_type: Optional[str] = None,
    search_q: Optional[str] = None,
    portal: Optional[str] = None,
    cross_listed_only: bool = False,
    open_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query enriched bids with flexible filtering."""
    query = "SELECT * FROM v_bids_enriched WHERE is_active = 1"
    params: list[Any] = []

    if agency_name:
        query += " AND (LOWER(agency_name_en) = LOWER(?) OR agency_name_dv = ?)"
        params.extend([agency_name, agency_name])

    if entity_slug:
        query += " AND entity_slug = ?"
        params.append(entity_slug)

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)

    if discipline:
        query += " AND discipline = ?"
        params.append(discipline)

    if procurement_nature:
        query += " AND procurement_nature = ?"
        params.append(procurement_nature)

    if gazette_type:
        query += " AND gazette_type = ?"
        params.append(gazette_type)

    if portal:
        query += " AND sources LIKE ?"
        params.append(f"%{portal}%")

    if cross_listed_only:
        query += " AND sources LIKE '%,%'"

    if search_q:
        query += " AND (LOWER(title) LIKE ? OR LOWER(title_en) LIKE ? OR LOWER(reference_number) LIKE ? OR LOWER(agency_name_en) LIKE ?)"
        term = f"%{search_q.lower()}%"
        params.extend([term, term, term, term])

    if open_only:
        now_iso = datetime.now().isoformat()
        query += " AND (submission_date IS NULL OR submission_date > ?)"
        params.append(now_iso)

    today_str = datetime.now().strftime("%Y-%m-%d")
    query += """
    ORDER BY
        CASE
            WHEN submission_date >= ? THEN 0
            WHEN submission_date IS NULL THEN 1
            ELSE 2
        END ASC,
        CASE
            WHEN submission_date >= ? THEN submission_date
        END ASC,
        submission_date DESC,
        published_date DESC
    LIMIT ?;
    """
    params.extend([today_str, today_str, limit])

    rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        # Parse document_urls from JSON string
        try:
            d["document_urls"] = json.loads(d["document_urls"]) if d.get("document_urls") else []
        except Exception:
            d["document_urls"] = []

        # Parse sources from JSON string
        try:
            d["sources"] = json.loads(d["sources"]) if d.get("sources") else ["gazette.gov.mv"]
        except Exception:
            d["sources"] = ["gazette.gov.mv"]

        d["is_cross_listed"] = len(d["sources"]) > 1

        # Maintain backwards compatibility with template keys
        d["ref"] = d["reference_number"]
        d["agency"] = d["agency_name_en"]
        d["deadline_iso"] = d["submission_date"]
        d["published_iso"] = d["published_date"]
        d["title_en"] = d.get("title_en") or d["title"]
        results.append(d)
    return results


def get_bids_filter_options(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Return sorted unique values for agencies, disciplines, and gazette types efficiently."""
    rows = conn.execute(
        """
        SELECT DISTINCT agency_name_en, discipline, gazette_type
        FROM v_bids_enriched
        WHERE is_active = 1;
        """
    ).fetchall()
    agencies = set()
    disciplines = set()
    types = set()
    for r in rows:
        if r["agency_name_en"]:
            agencies.add(r["agency_name_en"])
        if r["discipline"]:
            disciplines.add(r["discipline"])
        if r["gazette_type"]:
            types.add(r["gazette_type"])
    return {
        "agencies": sorted(agencies),
        "disciplines": sorted(disciplines),
        "types": sorted(types),
    }


def get_agency_portal_statistics(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return counts of tenders per agency and cross-source repetition statistics."""
    rows = conn.execute("SELECT id, agency_name_en, sources FROM v_bids_enriched WHERE is_active = 1;").fetchall()
    by_agency: dict[str, dict[str, int]] = {}
    total_bids = len(rows)
    cross_listed_count = 0
    portal_counts: dict[str, int] = {}

    for r in rows:
        agency = r["agency_name_en"] or "Unknown Agency"
        by_agency.setdefault(agency, {"total": 0, "cross_listed": 0})
        by_agency[agency]["total"] += 1

        try:
            srcs = json.loads(r["sources"]) if r["sources"] else ["gazette.gov.mv"]
        except Exception:
            srcs = ["gazette.gov.mv"]

        for s in srcs:
            portal_counts[s] = portal_counts.get(s, 0) + 1

        if len(srcs) > 1:
            cross_listed_count += 1
            by_agency[agency]["cross_listed"] += 1

    return {
        "total_bids": total_bids,
        "cross_listed_bids": cross_listed_count,
        "cross_listed_count": cross_listed_count,
        "by_agency": by_agency,
        "by_portal": portal_counts,
        "portal_counts": portal_counts,
    }

from data.repos.bid_milestones import extract_milestones_and_venues, purge_expired_bids
