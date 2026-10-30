"""
Scraper for gazette.gov.mv -- the Maldives Government Gazette.
Pure scraper and HTML parser module: zero database or alert dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Optional

from bs4 import BeautifulSoup
import requests

from scrapers.common.headers import DEFAULT_BROWSER_HEADERS as GAZETTE_HEADERS
from scrapers.tenders.classifier import (
    DISCIPLINE_KEYWORDS,
    classify_discipline,
    classify_procurement,
)
from scrapers.tenders.milestones import extract_milestones_and_venues

BASE_URL = "https://gazette.gov.mv"

TYPE_SLUGS = {
    "beelan": "Bid",
    "masakkaiy": "Work",
    "gannan-beynunvaa": "Goods to purchase",
    "kuyyah-dhinun": "Rent out",
    "kuyyah-hifun": "Rent in",
    "vazeefaa": "Job vacancy",
    "thamreenu": "Training",
    "neelan": "Auction",
    "aanmu-mauloomaathu": "Public information",
    "dhennevun": "Notice",
    "mubaaraaiy": "Competition",
    "noos-bayaan": "Press statement",
    "insurance": "Insurance",
}

TYPES = {
    "Beelan": "Bid",
    "Masakkathu": "Work",
    "Ganna Beynunvaa Thakethi": "Goods to purchase",
    "Kuiyah Dhinun": "Rent out",
    "Kuiyah Hifun": "Rent in",
    "Vazheefaage Furusathu": "Job vacancy",
    "Thamreenu": "Training",
    "Neelan": "Auction",
    "Aanmu Maulhoomaathu": "Public information",
    "Dhennevun": "Notice",
    "Mubaaraathu": "Competition",
    "Nooasbayaan": "Press statement",
    "Insurance": "Insurance",
    "ބީލަން": "Bid",
    "މަސައްކަތް": "Work",
    "ގަންނަން ބޭނުންވާ ތަކެތި": "Goods to purchase",
}

BID_ADJACENT_TYPES = {
    "Beelan", "Masakkathu", "Ganna Beynunvaa Thakethi",
    "Work", "Goods to purchase", "Bid",
    "ބީލަން", "މަސައްކަތް", "ގަންނަން ބޭނުންވާ ތަކެތި",
}

BID_TITLE_PATTERNS = re.compile(
    r"invitation for bids|invitation to bid|\bifb\b|tender notice|"
    r"request for proposal|\brfp\b|sealed bids|ބީލަން|މަސައްކަތް|ދަނޑު ކުއްޔަށް",
    re.IGNORECASE,
)


def print_url(notice_id: str) -> str:
    return f"{BASE_URL}/iulaan/print/{notice_id}"


def notice_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/iulaan/(?:print/|view/)?(\d+)", url)
    return m.group(1) if m else None


THAANA_MONTHS = {
    "ޖެނުއަރީ": 1, "ފެބްރުއަރީ": 2, "މާރޗް": 3, "މާރިޗު": 3,
    "އޭޕްރިލް": 4, "އޭޕްރީލް": 4, "މޭ": 5, "ޖޫން": 6,
    "ޖުލައި": 7, "އޯގަސްޓް": 8, "އޮގަސްޓް": 8,
    "ސެޕްޓެމްބަރ": 9, "ސެޕްޓެމްބަރު": 9, "ސެޕްޓެންބަރ": 9, "ސެޕްޓެންބަރު": 9,
    "އޮކްޓޯބަރ": 10, "އޮކްޓޫބަރު": 10,
    "ނޮވެމްބަރ": 11, "ނޮވެމްބަރު": 11, "ނޮވެންބަރ": 11, "ނޮވެންބަރު": 11,
    "ޑިސެމްބަރ": 12, "ޑިސެމްބަރު": 12, "ޑިސެންބަރ": 12, "ޑިސެންބަރު": 12,
}

ENGLISH_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}

ALL_MONTHS = {**THAANA_MONTHS, **ENGLISH_MONTHS}


def parse_published(date_str: str, time_str: Optional[str] = None) -> Optional[str]:
    """Parse published date + optional time into ISO string. Supports English & Thaana."""
    if not date_str:
        return None
    raw = f"{date_str} {time_str}" if time_str else date_str
    clean = re.sub(r"[\u200E\u200F\u200B\r\n\t]+", " ", raw).strip()
    clean = re.sub(
        r"^(?:ތާރީޚު|ޕަބްލިޝްކުރި ތާރީޚް|Published Date)\s*:\s*",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    m = re.search(r"(\d{1,2})\s+([^\d\s]+)\s+(\d{4})(?:\s+(\d{1,2}:\d{2}))?", clean)
    if m:
        day, mon_str, year, tm = m.groups()
        mon = ALL_MONTHS.get(mon_str.lower())
        if mon:
            hour, minute = (tm.split(":") if tm else ("00", "00"))
            try:
                dt = datetime(int(year), mon, int(day), int(hour), int(minute))
                return dt.isoformat()
            except ValueError:
                return None
    return None


def parse_deadline(deadline_str: str) -> Optional[str]:
    """Parse deadline string (date + time) into ISO string. Supports English & Thaana."""
    if not deadline_str:
        return None
    clean = re.sub(r"[\u200E\u200F\u200B\r\n\t]+", " ", deadline_str).strip()
    clean = re.sub(r"^(?:ސުންގަޑި|Deadline)\s*:\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"(\d+)\s*(?:st|nd|rd|th)\b", r"\1", clean, flags=re.IGNORECASE)

    m1 = re.search(r"(\d{1,2})\s+([^\d\s,]+)\s+(\d{4})(?:[^\d\n]*?(\d{1,2}:\d{2})(?:\s*(AM|PM))?)?", clean, re.IGNORECASE)
    m2 = re.search(r"(\d{4})\s+([^\d\s,]+)\s+(\d{1,2})(?:[^\d\n]*?(\d{1,2}:\d{2})(?:\s*(AM|PM))?)?", clean, re.IGNORECASE)

    if m1 and m1.group(2).lower() in ALL_MONTHS:
        day, mon_str, year, tm, ampm = m1.groups()
        mon = ALL_MONTHS[mon_str.lower()]
    elif m2 and m2.group(2).lower() in ALL_MONTHS:
        year, mon_str, day, tm, ampm = m2.groups()
        mon = ALL_MONTHS[mon_str.lower()]
    else:
        return None

    hour, minute = (tm.split(":") if tm else ("00", "00"))
    h = int(hour)
    if ampm:
        if ampm.upper() == "PM" and h < 12:
            h += 12
        elif ampm.upper() == "AM" and h == 12:
            h = 0
    try:
        dt = datetime(int(year), mon, int(day), h, int(minute))
        return dt.isoformat()
    except ValueError:
        return None


@dataclass
class BidNotice:
    notice_id: str
    url: str
    gazette_type: str
    reference_number: str
    published_iso: Optional[str]
    deadline_iso: Optional[str]
    agency: str
    title: str
    body: Optional[str] = None
    discipline: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    document_urls: list[str] = field(default_factory=list)
    submission_location: Optional[str] = None
    info_date: Optional[str] = None
    info_location: Optional[str] = None

    @property
    def is_open(self) -> bool:
        if not self.deadline_iso:
            return True
        try:
            deadline = datetime.fromisoformat(self.deadline_iso)
            now = datetime.now(deadline.tzinfo) if deadline.tzinfo else datetime.now()
            return deadline > now
        except Exception:
            return True

    def to_source_record(self) -> Any:
        from scrapers.dedupe import SourceRecord
        return SourceRecord(
            source_name="gazette.gov.mv",
            source_url=self.url,
            reference_number=self.reference_number or None,
            agency=self.agency,
            title=self.title,
            published_iso=self.published_iso,
            deadline_iso=self.deadline_iso,
            document_urls=self.document_urls,
            submission_location=self.submission_location,
            info_date=self.info_date,
            info_location=self.info_location,
        )


def parse_notice_html(html: str, notice_id: str) -> BidNotice:
    """Parse the raw HTML of a gazette print view (/iulaan/print/{id})."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    def field_after(label: str) -> Optional[str]:
        m = re.search(rf"{label}:\s*([^\n]+)", text)
        return m.group(1).strip() if m else None

    title_el = soup.select_one(".iulaan-title") or soup.find("h1") or soup.find("h2")
    title = title_el.get_text(strip=True) if title_el else ""

    agency_el = soup.select_one(".office-name") or soup.select_one(".office-info")
    agency = agency_el.get_text(strip=True) if agency_el else ""

    type_el = soup.select_one(".iulaan-info b")
    gazette_type = type_el.get_text(strip=True) if type_el else text.split("\n", 1)[0].strip()

    ref_el = soup.select_one(".iulaan-info .info span.en")
    if ref_el:
        reference_number = ref_el.get_text(strip=True)
    else:
        reference_number = field_after("Number") or field_after("ނަންބަރު") or ""

    pub_date = field_after("Published Date") or field_after("ޕަބްލިޝްކުރި ތާރީޚް") or ""
    pub_time = field_after("Published Time") or field_after("ޕަބްލިޝްކުރި ގަޑި") or ""
    published_iso = parse_published(pub_date, pub_time)

    deadline_raw = field_after("Deadline") or field_after("ސުންގަޑި") or ""
    deadline_iso = parse_deadline(deadline_raw)

    details_el = None
    for el in soup.select(".en-details, .details"):
        if el.get_text(strip=True):
            details_el = el
            break

    body = details_el.get_text("\n", strip=True) if details_el else ""

    document_urls: list[str] = []
    if details_el:
        for a in details_el.find_all("a", href=True):
            href = a["href"].strip()
            if (
                href
                and not href.startswith("mailto:")
                and not href.startswith("tel:")
                and not href.startswith("/cdn-cgi/")
            ):
                document_urls.append(href)

    milestones = extract_milestones_and_venues(html)

    if not deadline_iso and milestones.get("submission_date"):
        deadline_iso = parse_deadline(milestones["submission_date"])

    return BidNotice(
        notice_id=notice_id,
        url=print_url(notice_id),
        gazette_type=gazette_type,
        reference_number=reference_number,
        published_iso=published_iso,
        deadline_iso=deadline_iso,
        agency=agency,
        title=title,
        body=body,
        document_urls=list(dict.fromkeys(document_urls)),
        submission_location=milestones.get("submission_location"),
        info_date=milestones.get("info_date"),
        info_location=milestones.get("info_location"),
    )


def parse_listing_html(html: str) -> list[BidNotice]:
    """Parse listing cards from /iulaan?type=... listing page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".items-list .items")
    notices: list[BidNotice] = []

    for card in cards:
        title_el = card.select_one(".iulaan-title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        notice_id = notice_id_from_url(href) or ""

        office_el = card.select_one(".iulaan-office")
        agency = office_el.get_text(strip=True) if office_el else ""

        type_el = card.select_one(".iulaan-type")
        gazette_type = type_el.get_text(strip=True) if type_el else ""

        published_iso = None
        deadline_iso = None
        for info in card.select(".info"):
            itxt = info.get_text(" ", strip=True)
            if "ތާރީޚު" in itxt or "Published" in itxt:
                published_iso = parse_published(itxt)
            elif "ސުންގަޑި" in itxt or "Deadline" in itxt:
                deadline_iso = parse_deadline(itxt)

        card_url = (
            f"{BASE_URL}/iulaan/{notice_id}"
            if notice_id
            else (f"{BASE_URL}{href}" if href.startswith("/") else (href or f"{BASE_URL}/iulaan"))
        )
        notices.append(
            BidNotice(
                notice_id=notice_id,
                url=card_url,
                gazette_type=gazette_type,
                reference_number="",
                published_iso=published_iso,
                deadline_iso=deadline_iso,
                agency=agency,
                title=title,
            )
        )
    return notices


def fetch_notice(notice_id: str, session=None) -> BidNotice:
    """Fetch notice details from Gazette print view."""
    session = session or requests.Session()
    session.headers.update(GAZETTE_HEADERS)
    url = print_url(notice_id)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return parse_notice_html(resp.text, notice_id)


def fetch_listing(type_slug: str = "beelan", page: int = 1, session=None) -> list[BidNotice]:
    """Fetch and parse one page of notices from the live gazette listing."""
    session = session or requests.Session()
    session.headers.update(GAZETTE_HEADERS)
    url = f"{BASE_URL}/iulaan?type={type_slug}&page={page}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return parse_listing_html(resp.text)


def classify_notices(notices: list[BidNotice], classifier=None) -> list[BidNotice]:
    """Assign discipline classifications to a list of BidNotice objects."""
    classifier = classifier or classify_discipline
    for n in notices:
        n.discipline = classifier(n.title)
    return notices
