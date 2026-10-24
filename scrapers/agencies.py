"""
Multi-source scrapers for Maldivian SOEs and Ministries.
Backwards-compatible facade re-exporting atomic tender scrapers from scrapers.tenders.
"""
from scrapers.tenders.base import SSL_CTX, HEADERS, get_soup as _get_soup
from scrapers.tenders.finance import parse_finance_tenders, fetch_finance_tenders
from scrapers.tenders.tourism import parse_tourism_tenders, fetch_tourism_tenders
from scrapers.tenders.mwsc import parse_mwsc_tenders, fetch_mwsc_tenders
from scrapers.tenders.stelco import parse_stelco_tenders, fetch_stelco_tenders
from scrapers.tenders.sto import parse_sto_tenders, fetch_sto_tenders
from scrapers.tenders.engine import fetch_all_agency_portals

__all__ = [
    "SSL_CTX",
    "HEADERS",
    "_get_soup",
    "parse_finance_tenders",
    "fetch_finance_tenders",
    "parse_tourism_tenders",
    "fetch_tourism_tenders",
    "parse_mwsc_tenders",
    "fetch_mwsc_tenders",
    "parse_stelco_tenders",
    "fetch_stelco_tenders",
    "parse_sto_tenders",
    "fetch_sto_tenders",
    "fetch_all_agency_portals",
]
