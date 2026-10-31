"""
iBay Maldives Rental Scraper Adapter (ibay.com.mv).
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

IBAY_RENTAL_CATEGORIES = [
    "https://ibay.com.mv/apartments-houses-for-rent-b25_0.html",
    "https://ibay.com.mv/room-for-rent-b601_0.html",
]


def _parse_ibay_page(html: str, seen_urls: set[str]) -> list[dict[str, Any]]:
    """Parse apartment/room listings from an iBay HTML listing page."""
    soup = BeautifulSoup(html, "html.parser")
    listings: list[dict[str, Any]] = []

    # First attempt: structured .latest-list-item containers
    containers = soup.find_all("div", class_="latest-list-item")
    if containers:
        for c in containers:
            # Anchor tag containing genuine title
            title_a = c.find("a", href=re.compile(r"-o\d+\.html"), string=lambda s: bool(s and len(s.strip()) > 5))
            if not title_a:
                # Fallback: scan all item links
                candidates = c.find_all("a", href=re.compile(r"-o\d+\.html"))
                for cand in candidates:
                    t = cand.get_text(strip=True)
                    if len(t) >= 5:
                        title_a = cand
                        break
            if not title_a:
                continue

            raw_href = title_a.get("href", "").split("?")[0].strip()
            if not raw_href or raw_href in seen_urls:
                continue
            canonical_url = raw_href if raw_href.startswith("http") else f"https://ibay.com.mv/{raw_href.lstrip('/')}"
            seen_urls.add(raw_href)

            title = title_a.get_text(strip=True)
            row_text = c.get_text(separator=" | ", strip=True)

            img_el = c.find("img")
            img_url = ""
            if img_el:
                img_url = img_el.get("data-src") or img_el.get("src") or ""
                if "no_image" in img_url or "lazyload" in img_url:
                    img_url = ""

            item = _build_rental_item(title, row_text, canonical_url, img_url)
            listings.append(item)
        return listings

    # Fallback parser if markup differs
    for a in soup.find_all("a", href=re.compile(r"-o\d+\.html")):
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        raw_href = a["href"].split("?")[0].strip()
        if not raw_href or raw_href in seen_urls:
            continue
        seen_urls.add(raw_href)
        canonical_url = raw_href if raw_href.startswith("http") else f"https://ibay.com.mv/{raw_href.lstrip('/')}"

        col = a.find_parent("div", class_="col")
        row = col.parent if col else a.parent
        row_text = row.get_text(separator=" | ", strip=True) if row else title
        listings.append(_build_rental_item(title, row_text, canonical_url, ""))

    return listings


def _build_rental_item(title: str, row_text: str, canonical_url: str, img_url: str) -> dict[str, Any]:
    """Extract attributes and construct standardized rental dictionary."""
    rent = 0
    price_m = re.search(r"MVR\s*\|\s*([\d,]+(?:\.\d+)?)", row_text, re.I)
    if not price_m:
        price_m = re.search(r"(?:MVR|Rf\.?)\s*([\d,]+)", f"{title} {row_text}", re.I)
    if price_m:
        try:
            rent = int(float(price_m.group(1).replace(",", "")))
        except ValueError:
            rent = 0
    if rent <= 0:
        digit_m = re.search(r"\b(1\d{4}|2\d{4}|3\d{4}|[4-9]\d{3})\b", title)
        if digit_m:
            try:
                rent = int(digit_m.group(1))
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

    return _item(
        title=title,
        loc=loc_str,
        dist=dist_str,
        road="Boduthakurufaanu Magu" if loc_str == "Male City" else "Nirolhu Magu",
        bld="Local Residence",
        total_f=total_floors,
        f_num=int(re.sub(r"[^\d]", "", floor_desc) or 3),
        f_str=floor_desc,
        unit=f"{beds}BHK",
        beds=beds,
        att=att,
        tot=tot,
        sqft=max(450, beds * 350),
        lift=lift,
        kitchen="Sitting Room / Kitchen",
        living="Sitting & Dining Area",
        ac="Installed in bedrooms",
        heaters=att,
        furn=furn,
        items=COMMON_FURNISHED_ITEMS if furn == "Fully Furnished" else COMMON_FURNISHED_ITEMS[:4],
        rent=rent if rent > 0 else 15000,
        sec_rent=None,
        sec_src=None,
        dep=rent if rent > 0 else 15000,
        src="iBay Maldives",
        url=canonical_url,
        sec_urls=[],
        img=img_url or "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80",
        parking="No In-Building Parking (Street Parking Only)",
        contact="iBay Lister",
        phone=phone if phone else "+960 7000000",
        desc=row_text[:250],
        ams=["Air Conditioning", "Water Heaters", "Sitting Room / Kitchen"],
        facs=["WAMCO Included", "24hr Security"],
    )


def scrape_ibay_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Dedicated scraper for iBay Maldives (ibay.com.mv).
    Fetches genuine live listings from iBay apartment & room categories or parses supplied raw HTML.
    """
    if raw_html is not None:
        return _parse_ibay_page(raw_html, set())

    all_listings: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for cat_url in IBAY_RENTAL_CATEGORIES:
        try:
            html = fetch_text(
                cat_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10,
                retries=2,
            )
            if not html:
                logger.warning("Failed fetching live listings from iBay category: %s", cat_url)
                continue
            cat_listings = _parse_ibay_page(html, seen_urls)
            all_listings.extend(cat_listings)
        except Exception as exc:
            logger.warning("Error scraping iBay category %s: %s", cat_url, exc)

    logger.info("iBay scraper fetched %d live rental listings.", len(all_listings))
    return all_listings
