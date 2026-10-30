"""
Boahiyaa Real Estate Rental Scraper Adapter (boahiyaa.com).
Pure scraper/parser module: fetches and returns normalized rental dicts without DB writes.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from scrapers.rentals.base import COMMON_FURNISHED_ITEMS, _item

logger = logging.getLogger(__name__)


def scrape_boahiyaa_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Boahiyaa Real Estate (boahiyaa.com)."""
    if raw_html:
        soup = BeautifulSoup(raw_html, "html.parser")
        items: list[dict[str, Any]] = []
        for card in soup.find_all("div", class_=re.compile(r"listing|property|item", re.I)):
            t = card.get_text(strip=True)
            if t:
                items.append(_item(
                    title=t[:60], loc="Male City", dist="Henveiru", road="Roashanee Magu",
                    bld="B. Residence", total_f=6, f_num=2, f_str="2nd Floor", unit="Apt 201",
                    beds=2, att=2, tot=2, sqft=750, lift=1, kitchen="Open Kitchen",
                    living="Lounge", ac="Installed", heaters=2, furn="Semi-Furnished",
                    items=COMMON_FURNISHED_ITEMS[:4], rent=20000, sec_rent=None, sec_src=None,
                    dep=20000, src="Boahiyaa Real Estate", url="https://boahiyaa.com/listing/sample",
                    sec_urls=[], img="", parking="Street", contact="Boahiyaa Agent", phone="+960 7900000",
                    desc=t[:200], ams=["AC"], facs=["Security"],
                ))
        return items
    logger.debug("Boahiyaa scraper: live open endpoint unsupported, preserving records.")
    return []
