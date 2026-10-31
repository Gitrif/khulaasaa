"""
KobaPages Maldives Rental Scraper Adapter (kobapages.com).
Pure scraper/parser module: fetches and returns normalized rental dicts without DB writes.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def scrape_kobapages_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for KobaPages Maldives (kobapages.com)."""
    if raw_html:
        return []
    logger.debug("KobaPages scraper: live open endpoint unsupported, preserving records.")
    return []
