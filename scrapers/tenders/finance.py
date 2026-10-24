"""
Ministry of Finance / National Tender Board Scraper (finance.gov.mv).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup

logger = logging.getLogger(__name__)

URL = "https://www.finance.gov.mv/tenders"


def parse_finance_tenders(html: str) -> list[SourceRecord]:
    """
    Parse tenders table from https://www.finance.gov.mv/tenders
    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []

    table = soup.find("table")
    if not table:
        return records

    rows = table.find_all("tr")
    for tr in rows[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 8:
            continue

        proj_type = cells[0]
        inv_ref = cells[1]
        proc_no = cells[2]
        title = cells[3]
        sector = cells[4]
        agency = cells[5] if len(cells) > 5 else "Ministry of Finance"
        pub_date = cells[7] if len(cells) > 7 else None
        sub_date = cells[8] if len(cells) > 8 else None

        pub_iso = None
        if pub_date:
            m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", pub_date)
            if m:
                d, mo, y = m.groups()
                pub_iso = f"{y}-{int(mo):02d}-{int(d):02d}"

        sub_iso = None
        if sub_date:
            m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}:\d{2}))?", sub_date)
            if m:
                d, mo, y, tm = m.groups()
                sub_iso = f"{y}-{int(mo):02d}-{int(d):02d}" + (f"T{tm}:00" if tm else "T10:00:00")

        primary_ref = inv_ref if inv_ref and inv_ref != "-" else proc_no

        link_el = tr.find("a", href=True)
        if link_el:
            href = link_el["href"]
            direct_source_url = href if href.startswith("http") else f"https://www.finance.gov.mv{href}"
        elif primary_ref:
            clean_ref = re.sub(r"[^A-Za-z0-9]+", "-", primary_ref).strip("-").lower()
            direct_source_url = f"https://www.finance.gov.mv/tenders/project/{clean_ref}"
        else:
            direct_source_url = URL

        records.append(
            SourceRecord(
                source_name="finance.gov.mv",
                source_url=direct_source_url,
                reference_number=primary_ref,
                agency=agency or "Ministry of Finance",
                title=title,
                published_iso=pub_iso,
                deadline_iso=sub_iso,
                submission_location="National Tender Board, Ministry of Finance, Ameenee Magu, Male'",
                info_location="National Tender Board, Ministry of Finance",
            )
        )
    return records


def fetch_finance_tenders(soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> list[SourceRecord]:
    """Fetch and parse live tenders from Ministry of Finance."""
    fetcher = soup_getter or get_soup
    soup = fetcher(URL)
    if not soup:
        return []
    return parse_finance_tenders(str(soup))
