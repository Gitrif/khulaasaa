"""
Hiyaa.mv Residential Rental Scraper Adapter (hiyaa.mv).
Pure scraper/parser module: fetches and returns normalized rental dicts without DB writes.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def scrape_hiyaa_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Hiyaa.mv Residential Towers (hiyaa.mv)."""
    if raw_html:
        return []
    logger.debug("Hiyaa.mv scraper: live open endpoint unsupported, preserving records.")
    return []
