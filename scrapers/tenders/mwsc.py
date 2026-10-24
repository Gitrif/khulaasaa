"""
Male' Water and Sewerage Company (MWSC) Tender Scraper (mwsc.com.mv).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup

logger = logging.getLogger(__name__)

URL = "https://www.mwsc.com.mv/tenders"


def parse_mwsc_tenders(html: str) -> list[SourceRecord]:
    """
    Parse tenders from https://www.mwsc.com.mv/tenders
    Table columns: Name, Deadline for Registration, Bid Submission Date, Info, Document
    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []

    table = soup.find("table")
    if not table:
        return records

    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) >= 3:
            name_text = cells[0].get_text(" ", strip=True)
            reg_deadline = cells[1].get_text(" ", strip=True)
            sub_date = cells[2].get_text(" ", strip=True)

            doc_urls = []
            link_el = cells[-1].find("a") if len(cells) > 4 else None
            if link_el and link_el.get("href"):
                doc_urls.append(link_el["href"])

            ref_m = re.search(r"\b(MWSC[^\s,]+|\(IUL\)[^\s,]+)", name_text)
            ref = ref_m.group(1) if ref_m else None

            if doc_urls:
                direct_url = doc_urls[0]
            elif ref:
                clean_ref = re.sub(r"[^A-Za-z0-9]+", "-", ref).strip("-").lower()
                direct_url = f"https://www.mwsc.com.mv/tenders/notice/{clean_ref}"
            else:
                direct_url = URL

            records.append(
                SourceRecord(
                    source_name="mwsc.com.mv",
                    source_url=direct_url,
                    reference_number=ref,
                    agency="Male' Water and Sewerage Company",
                    title=name_text,
                    published_iso=None,
                    deadline_iso=None,
                    document_urls=doc_urls,
                    info_date=reg_deadline if reg_deadline and reg_deadline != "-" else None,
                    info_location="MWSC Online Vendor Portal",
                    submission_location="MWSC Customer Building 3rd Floor / Procurement Dept",
                )
            )
    return records


def fetch_mwsc_tenders(soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> list[SourceRecord]:
    """Fetch and parse live tenders from MWSC."""
    fetcher = soup_getter or get_soup
    soup = fetcher(URL)
    if not soup:
        return []
    return parse_mwsc_tenders(str(soup))
