"""
Ministry of Tourism Bidding Announcements Scraper (tourism.gov.mv).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.tenders.base import get_soup

logger = logging.getLogger(__name__)

URL = "https://www.tourism.gov.mv/en/page/bidding_announcements"


def parse_tourism_tenders(html: str) -> list[SourceRecord]:
    """
    Parse bidding announcements from https://www.tourism.gov.mv/en/page/bidding_announcements
    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    records: list[SourceRecord] = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            if tr.find_all("th") and not tr.find_all("td"):
                continue
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) >= 2:
                date_str = cells[0]
                text = cells[1]

                if text.lower() in ("announcement", "announcements", "title", "subject", "details"):
                    continue

                ref_m = re.search(r"\(IUL\)[A-Za-z0-9_/-]+", text, re.IGNORECASE)
                ref = ref_m.group(0) if ref_m else None

                title = re.sub(r"-\s*\(IUL\)[A-Za-z0-9_/-]+", "", text, flags=re.IGNORECASE).strip()
                title = re.sub(r"\(IUL\)[A-Za-z0-9_/-]+", "", title, flags=re.IGNORECASE).strip()
                title = re.sub(r"-\s*$", "", title).strip()

                if len(title) > 10 and not any(k in title.lower() for k in ["nothing to view", "sample"]):
                    records.append(
                        SourceRecord(
                            source_name="tourism.gov.mv",
                            source_url=URL,
                            reference_number=ref,
                            agency="Ministry of Tourism",
                            title=title,
                            published_iso=None,
                            deadline_iso=None,
                            submission_location="Ministry of Tourism, Velaanaage, 5th Floor, Male'",
                        )
                    )
    return records


def fetch_tourism_tenders(soup_getter: Optional[Callable[[str], Optional[bs4.BeautifulSoup]]] = None) -> list[SourceRecord]:
    """Fetch and parse live tenders from Ministry of Tourism."""
    fetcher = soup_getter or get_soup
    soup = fetcher(URL)
    if not soup:
        return []
    return parse_tourism_tenders(str(soup))
