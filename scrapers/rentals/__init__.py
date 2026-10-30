"""
Khulaasaa Rentals Scraper Package.
Provides pure rental scraper adapters, parsers, and cross-portal consolidation.
Database persistence lives in data.repos.rentals and orchestration in services.ingestion.rentals_ingestion.
"""
from __future__ import annotations

from scrapers.rentals.base import (
    COMMON_FURNISHED_ITEMS,
    RENTAL_SOURCES,
    _item,
    consolidate_key,
    detect_leased_status,
    extract_lift_and_floors,
    extract_rooms_and_toilets,
    normalize_location,
)
from scrapers.rentals.boahiyaa import scrape_boahiyaa_rentals
from scrapers.rentals.engine import (
    DEFAULT_RENTAL_SCRAPERS,
    SCRAPER_MAP,
    fetch_and_consolidate_rentals,
)
from scrapers.rentals.hiyaa import scrape_hiyaa_rentals
from scrapers.rentals.ibay import scrape_ibay_rentals
from scrapers.rentals.kobapages import scrape_kobapages_rentals
from scrapers.rentals.propertymv import scrape_propertymv_rentals

__all__ = [
    "COMMON_FURNISHED_ITEMS",
    "DEFAULT_RENTAL_SCRAPERS",
    "RENTAL_SOURCES",
    "SCRAPER_MAP",
    "_item",
    "consolidate_key",
    "detect_leased_status",
    "extract_lift_and_floors",
    "extract_rooms_and_toilets",
    "fetch_and_consolidate_rentals",
    "normalize_location",
    "scrape_boahiyaa_rentals",
    "scrape_hiyaa_rentals",
    "scrape_ibay_rentals",
    "scrape_kobapages_rentals",
    "scrape_propertymv_rentals",
]
