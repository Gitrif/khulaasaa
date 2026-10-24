"""
State Electric Company (STELCO) Tender Scraper (stelco.com.mv).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup
from scrapers.gazette import ALL_MONTHS

logger = logging.getLogger(__name__)

URL = "https://stelco.com.mv/tenders"


def parse_stelco_tenders(html: str) -> list[SourceRecord]:
    """
    Parse tenders from https://stelco.com.mv/tenders
    Extracts all package listings, checks expiration status, and parses deadlines.
    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []

    items = []
    package_links = soup.find_all("a", class_="package-title")
    if package_links:
        for a in package_links:
            items.append((a.get_text(" ", strip=True), a.get("href", ""), a.find_parent("tr")))
    else:
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue
            a_el = cells[0].find("a")
            href = a_el.get("href", "") if a_el else ""
            items.append((cells[0].get_text(" ", strip=True), href, tr))

    for full_text, href, tr in items:
        btn = tr.find("button") if tr else None
        btn_text = btn.get_text(" ", strip=True) if btn else ""
        btn_title = btn.get("title", "") if btn else ""
        is_expired = (
            "expired" in btn_text.lower()
            or "expired" in btn_title.lower()
            or (tr and "expired" in tr.get_text().lower())
        )

        deadline_iso = None
        exp_m = re.search(
            r"expired\s+on\s+([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})(?:\s+(\d{1,2}:\d{2})\s*(AM|PM)?)?",
            btn_title or (tr.get_text() if tr else ""),
            re.IGNORECASE,
        )
        if exp_m:
            mon_str, day, year, tm, ampm = exp_m.groups()
            mon = ALL_MONTHS.get(mon_str.lower(), 1)
            h, m_min = (tm.split(":") if tm else ("20", "00"))
            h_int = int(h)
            if ampm and ampm.upper() == "PM" and h_int < 12:
                h_int += 12
            deadline_iso = f"{year}-{mon:02d}-{int(day):02d}T{h_int:02d}:{m_min}:00"

        ref_m = re.search(r"([A-Za-z0-9\(\)]+/[A-Za-z0-9/-]+)", full_text)
        ref = ref_m.group(1) if ref_m else None

        clean_title = full_text
        if ref:
            clean_title = clean_title.replace(ref, "").strip(", -")
        clean_title = re.sub(r"\d+\s+file\(s\)\s+\d+\s+downloads", "", clean_title).strip()

        if clean_title:
            records.append(
                SourceRecord(
                    source_name="stelco.com.mv",
                    source_url=href or URL,
                    reference_number=ref,
                    agency="State Electric Company",
                    title=clean_title,
                    published_iso=None,
                    deadline_iso=deadline_iso,
                    submission_location="STELCO Head Office 2nd Floor, Male'",
                )
            )

    return records


def fetch_stelco_tenders(soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> list[SourceRecord]:
    """Fetch and parse live tenders from STELCO."""
    fetcher = soup_getter or get_soup
    soup = fetcher(URL)
    if not soup:
        return []
    return parse_stelco_tenders(str(soup))
