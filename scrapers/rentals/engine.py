"""
Rentals Scraper Engine & Multi-Portal Consolidator.
Fetches rental listings from iBay, Boahiyaa, Hiyaa.mv, Property.mv, and KobaPages.
Pure scraper/consolidator module: zero database writes.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from scrapers.rentals.boahiyaa import scrape_boahiyaa_rentals
from scrapers.rentals.hiyaa import scrape_hiyaa_rentals
from scrapers.rentals.ibay import scrape_ibay_rentals
from scrapers.rentals.kobapages import scrape_kobapages_rentals
from scrapers.rentals.propertymv import scrape_propertymv_rentals

logger = logging.getLogger(__name__)

DEFAULT_RENTAL_SCRAPERS: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = [
    ("iBay Maldives", scrape_ibay_rentals),
    ("Boahiyaa Real Estate", scrape_boahiyaa_rentals),
    ("Hiyaa.mv", scrape_hiyaa_rentals),
    ("Property.mv", scrape_propertymv_rentals),
    ("KobaPages", scrape_kobapages_rentals),
]

SCRAPER_MAP: dict[str, Callable[[], list[dict[str, Any]]]] = {
    "ibay": scrape_ibay_rentals,
    "boahiyaa": scrape_boahiyaa_rentals,
    "hiyaa": scrape_hiyaa_rentals,
    "propertymv": scrape_propertymv_rentals,
    "kobapages": scrape_kobapages_rentals,
}


def fetch_and_consolidate_rentals(
    sources: Optional[list] = None,
) -> tuple[list[dict[str, Any]], list[str], int]:
    """
    Run configured rental scrapers and return (all_scraped_items, errors, sources_attempted).
    Supports either a list of (name, callable) tuples or a list of source key strings.
    """
    scrapers = sources or DEFAULT_RENTAL_SCRAPERS
    all_scraped: list[dict[str, Any]] = []
    errors: list[str] = []

    for entry in scrapers:
        if isinstance(entry, tuple) and len(entry) == 2:
            name, scraper_fn = entry
        else:
            name = str(entry)
            scraper_fn = SCRAPER_MAP.get(name.lower())
            if not scraper_fn:
                continue
        try:
            items = scraper_fn()
            logger.info("Rental source %s yielded %d listings", name, len(items))
            all_scraped.extend(items)
        except Exception as exc:
            logger.warning("Rental scraper failed for %s: %s", name, exc)
            errors.append(f"{name}: {exc}")

    return all_scraped, errors, len(scrapers)
