"""
Procurement & Tender Scrapers Package.
"""
from __future__ import annotations

from scrapers.tenders.base import HEADERS, SSL_CTX, get_soup
from scrapers.tenders.classifier import (
    DISCIPLINE_KEYWORDS,
    classify_discipline,
    classify_procurement,
)
from scrapers.tenders.engine import fetch_all_agency_portals
from scrapers.tenders.finance import fetch_finance_tenders, parse_finance_tenders
from scrapers.tenders.gazette import (
    BASE_URL,
    BID_ADJACENT_TYPES,
    BID_TITLE_PATTERNS,
    GAZETTE_HEADERS,
    TYPES,
    TYPE_SLUGS,
    BidNotice,
    classify_notices,
    fetch_listing,
    fetch_notice,
    notice_id_from_url,
    parse_deadline,
    parse_listing_html,
    parse_notice_html,
    parse_published,
    print_url,
)
from scrapers.tenders.milestones import extract_milestones_and_venues
from scrapers.tenders.mwsc import fetch_mwsc_tenders, parse_mwsc_tenders
from scrapers.tenders.stelco import fetch_stelco_tenders, parse_stelco_tenders
from scrapers.tenders.sto import fetch_sto_tenders, parse_sto_tenders
from scrapers.tenders.tourism import fetch_tourism_tenders, parse_tourism_tenders

_get_soup = get_soup

__all__ = [
    "BASE_URL",
    "BID_ADJACENT_TYPES",
    "BID_TITLE_PATTERNS",
    "DISCIPLINE_KEYWORDS",
    "GAZETTE_HEADERS",
    "HEADERS",
    "SSL_CTX",
    "TYPES",
    "TYPE_SLUGS",
    "BidNotice",
    "_get_soup",
    "classify_discipline",
    "classify_notices",
    "classify_procurement",
    "extract_milestones_and_venues",
    "fetch_all_agency_portals",
    "fetch_finance_tenders",
    "fetch_listing",
    "fetch_mwsc_tenders",
    "fetch_notice",
    "fetch_stelco_tenders",
    "fetch_sto_tenders",
    "fetch_tourism_tenders",
    "get_soup",
    "notice_id_from_url",
    "parse_deadline",
    "parse_finance_tenders",
    "parse_listing_html",
    "parse_mwsc_tenders",
    "parse_notice_html",
    "parse_published",
    "parse_stelco_tenders",
    "parse_sto_tenders",
    "parse_tourism_tenders",
    "print_url",
]
