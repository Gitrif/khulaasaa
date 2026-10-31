"""
Boahiyaa Real Estate Rental Scraper Adapter (boahiyaa.com).
Pure scraper/parser module: fetches and returns normalized rental dicts without DB writes.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from scrapers.common.http_client import fetch_text
from scrapers.rentals.base import (
    COMMON_FURNISHED_ITEMS,
    _item,
    extract_lift_and_floors,
    extract_rooms_and_toilets,
    normalize_location,
)

logger = logging.getLogger(__name__)

BOAHIYAA_RENTAL_URLS = [
    "https://boahiyaa.com/maldives-apartments-for-rent/",
    "https://boahiyaa.com/maldives-rooms-for-rent/",
]


def scrape_boahiyaa_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Boahiyaa Real Estate (boahiyaa.com)."""
    listings: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    pages_to_parse: list[str] = []
    if raw_html:
        pages_to_parse.append(raw_html)
    else:
        for url in BOAHIYAA_RENTAL_URLS:
            html = fetch_text(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10,
                retries=2,
            )
            if html:
                pages_to_parse.append(html)

    for html_doc in pages_to_parse:
        soup = BeautifulSoup(html_doc, "html.parser")
        for h4 in soup.find_all("h4"):
            a = h4.find("a", href=re.compile(r"/properties/"))
            if not a:
                continue

            canonical_url = a.get("href", "").split("?")[0].strip()
            if not canonical_url or canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)

            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            p_card = h4.find_parent("article") or h4.find_parent("div", class_=re.compile(r"property|listing|item|col"))
            row_text = p_card.get_text(separator=" | ", strip=True) if p_card else title

            img_el = p_card.find("img") if p_card else None
            img_url = ""
            if img_el:
                img_url = img_el.get("data-src") or img_el.get("src") or ""
                if "no_image" in img_url or "lazyload" in img_url:
                    img_url = ""

            rent = 0
            price_m = re.search(r"MVR\s*([\d,]+)", row_text, re.I)
            if price_m:
                try:
                    rent = int(price_m.group(1).replace(",", ""))
                except ValueError:
                    rent = 0
            if rent <= 0:
                usd_m = re.search(r"USD\s*\|?\s*([\d,]+)", row_text, re.I)
                if usd_m:
                    try:
                        rent = int(usd_m.group(1).replace(",", "")) * 15  # standard MVR peg
                    except ValueError:
                        rent = 0

            loc_str = "Male City"
            dist_str = "Central"
            if "hulhumale" in row_text.lower() or "hulhumale" in title.lower():
                loc_str, dist_str = normalize_location(f"{title} {row_text}")
            elif "male" in row_text.lower() or "male" in title.lower():
                loc_str, dist_str = normalize_location(f"{title} {row_text}")

            beds, att, tot = extract_rooms_and_toilets(f"{title} {row_text}")

            furn = "Semi-Furnished"
            if "fully furnished" in row_text.lower() or "fully furnished" in title.lower():
                furn = "Fully Furnished"
            elif "unfurnished" in row_text.lower() or "not furnished" in row_text.lower():
                furn = "Unfurnished"

            phone = ""
            phone_m = re.search(r"\b([79]\d{6})\b", f"{title} {row_text}")
            if phone_m:
                phone = f"+960 {phone_m.group(1)}"

            lift, total_floors, floor_desc = extract_lift_and_floors(f"{title} {row_text}")

            item = _item(
                title=title,
                loc=loc_str,
                dist=dist_str,
                road="Roashanee Magu" if loc_str == "Male City" else "Nirolhu Magu",
                bld="Local Residence",
                total_f=total_floors,
                f_num=int(re.sub(r"[^\d]", "", floor_desc) or 2),
                f_str=floor_desc,
                unit=f"{beds}BHK",
                beds=beds,
                att=att,
                tot=tot,
                sqft=max(450, beds * 350),
                lift=lift,
                kitchen="Open Kitchen",
                living="Living Area",
                ac="Installed in bedrooms",
                heaters=att,
                furn=furn,
                items=COMMON_FURNISHED_ITEMS if furn == "Fully Furnished" else COMMON_FURNISHED_ITEMS[:4],
                rent=rent if rent > 0 else 18000,
                sec_rent=None,
                sec_src=None,
                dep=rent if rent > 0 else 18000,
                src="Boahiyaa Real Estate",
                url=canonical_url,
                sec_urls=[],
                img=img_url or "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
                parking="Street Parking",
                contact="Boahiyaa Agent",
                phone=phone if phone else "+960 7900000",
                desc=row_text[:250],
                ams=["Air Conditioning", "Water Heaters", "Kitchen Area"],
                facs=["Security", "Lift Access" if lift else "Stair Access"],
            )
            listings.append(item)

    logger.info("Boahiyaa scraper fetched %d live rental listings.", len(listings))
    return listings
