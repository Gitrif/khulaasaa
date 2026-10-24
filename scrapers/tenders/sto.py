"""
State Trading Organization (STO) Tender Scraper (sto.mv).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup

logger = logging.getLogger(__name__)

URL = "https://www.sto.mv/newsroom/tenders"


def parse_sto_tenders(html: str) -> list[SourceRecord]:
    """
    Parse tender listings from https://www.sto.mv/newsroom/tenders
    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/newsroom/tenders/" in href and not href.endswith("/archive") and not href.endswith("/tenders"):
            text = a.get_text(" ", strip=True)
            ref_m = re.search(r"(\d+-[A-Z]+/\d+/\d+)", text)
            ref = ref_m.group(1) if ref_m else None

            full_url = href if href.startswith("http") else f"https://www.sto.mv{href}"
            clean_title = text
            if ref:
                clean_title = clean_title.replace(ref, "").strip(" -")
            clean_title = re.sub(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}", "", clean_title).strip()

            if len(clean_title) > 10:
                records.append(
                    SourceRecord(
                        source_name="sto.mv",
                        source_url=full_url,
                        reference_number=ref,
                        agency="State Trading Organization",
                        title=clean_title,
                        published_iso=None,
                        deadline_iso=None,
                        submission_location="STO Head Office Reception, Boduthakurufaanu Magu, Male'",
                    )
                )
    return records


def fetch_sto_tenders(soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> list[SourceRecord]:
    """Fetch and parse live tenders from STO."""
    fetcher = soup_getter or get_soup
    soup = fetcher(URL)
    if not soup:
        return []
    return parse_sto_tenders(str(soup))
