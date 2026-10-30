"""
Procurement & Tender Scraper Orchestration Engine.
Runs scrapers across all Maldivian agencies and SOEs concurrently with soft-fail resilience.
"""
from __future__ import annotations

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup
from scrapers.tenders.finance import fetch_finance_tenders
from scrapers.tenders.tourism import fetch_tourism_tenders
from scrapers.tenders.mwsc import fetch_mwsc_tenders
from scrapers.tenders.stelco import fetch_stelco_tenders
from scrapers.tenders.sto import fetch_sto_tenders

logger = logging.getLogger(__name__)


def _resolve_soup_getter(override: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> Callable[[str], Optional[bs4.BeautifulSoup]]:
    if override is not None:
        return override
    for mod_name in ("scrapers.tenders", "scrapers.agencies"):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, "_get_soup"):
            return mod._get_soup
    return get_soup


def fetch_all_agency_portals(
    max_workers: int = 5,
    soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None,
) -> list[SourceRecord]:
    """
    Polls all supported SOE and Ministry tender pages concurrently.
    Network errors on individual portals fail soft so aggregation continues.
    """
    effective_soup = _resolve_soup_getter(soup_getter)
    all_records: list[SourceRecord] = []

    agency_fetchers = [
        ("Ministry of Finance", lambda: fetch_finance_tenders(effective_soup)),
        ("Ministry of Tourism", lambda: fetch_tourism_tenders(effective_soup)),
        ("MWSC", lambda: fetch_mwsc_tenders(effective_soup)),
        ("STELCO", lambda: fetch_stelco_tenders(effective_soup)),
        ("STO", lambda: fetch_sto_tenders(effective_soup)),
    ]

    def _safe_fetch(item: tuple[str, Callable[[], list[SourceRecord]]]) -> list[SourceRecord]:
        name, fetcher = item
        try:
            records = fetcher()
            logger.info("Fetched %d tenders from %s", len(records), name)
            return records
        except Exception as exc:
            logger.warning("Failed to fetch tenders from %s: %s", name, exc)
            return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_safe_fetch, agency_fetchers)
        for records in results:
            all_records.extend(records)

    return all_records
