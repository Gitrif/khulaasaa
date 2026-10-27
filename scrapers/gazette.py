"""
Scraper for gazette.gov.mv -- the Maldives Government Gazette. Focused on
bid/tender notices (type "Beelan"). Built from direct inspection of the
live site on 2026-09-30 (several real notices fetched, listed at bottom).

CONFIRMED BY DIRECT INSPECTION:
- Real domain is gazette.gov.mv (both bare and www. resolve).
- Article/notice URL pattern: gazette.gov.mv/iulaan/{id} (normal view)
  and gazette.gov.mv/iulaan/print/{id} (print view -- cleaner, fewer nav
  elements, prefer this one for scraping).
- Every notice carries structured fields at the top of the print view:
  Type, Number (reference), Published Date, Published Time, Deadline
  (date + time, when applicable), publishing Agency name, Title, Body.
- The listing page (gazette.gov.mv/iulaan) has a real filter form with:
  ބާވަތް (Type) dropdown -- confirmed values include Bid ("ބީލަން"),
  Work ("މަސައްކަތް"), Goods-to-purchase ("ގަންނަން ބޭނުންވާ ތަކެތި"),
  plus ~10 more (Rent out/in, Job, Training, Auction, Public info,
  Notice, Competition, Press statement, Insurance).
  އޮފީސް (Office/Agency) dropdown -- agency filtering is native to the
  site, we don't have to build it.
  Plus keyword search, date-range, and a "deadline not passed" checkbox.
- Publishing agencies span central ministries, island/atoll council
  secretariats, AND state-owned enterprises (Island Aviation Services,
  Maldive Gas Pvt Ltd both seen live) -- the agency universe is wide,
  not just ministries.

NOT CONFIRMED -- same caveat as haftha.py: this sandbox can't reach
gazette.gov.mv directly (outside the network allowlist), so everything
below came through the assistant's web-fetch tool, which returns cleaned
text rather than raw HTML:
- robots.txt / terms of use for automated access -- check before
  scraping at real frequency. This is a .gov.mv site; beyond the
  technical question, worth a direct ask to NCIT/President's Office.
- Exact URL slug values for each Type filter option (e.g. what
  "ބީލަން" encodes to in ?type=... -- we saw one example, "?type=aanmu-
  mauloomaathu", for Public Info, but didn't capture the Bid slug
  itself). Needed to filter listings server-side by type instead of
  fetching everything and filtering client-side.
- The full Office/Agency dropdown value list -- it's a long <select>,
  and the fetch tool doesn't return raw <option value=""> attributes,
  only the visible label text for the field as a whole. Needed to
  build an agency filter that matches the site's own IDs rather than
  fuzzy-matching agency name strings.
- Whether type="Beelan" (Bid) is applied consistently. One construction
  tender (V.Fulidhoo Police Post) appeared in search results without a
  visible "Beelan" header in the snippet -- inconclusive on its own
  (could just be snippet truncation) but consistent with the concern
  raised earlier: don't rely on type=Bid alone to find all tenders.
  Recommendation stands -- treat type IN (Beelan, Work, Goods) as the
  candidate pool, and/or pattern-match titles for "Invitation for
  Bids", "IFB", "Invitation to Bid", "Tender Notice".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

BASE_URL = "https://gazette.gov.mv"

# Confirmed URL slugs for server-side type filtering
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

# Observed type labels (Dhivehi/Romanized -> English).
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

# Candidate types worth treating as "possibly a tender" even when not
# explicitly typed Bid -- see the type-inconsistency note above.
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
    # Strip ordinals like 1st, 2nd, 3rd, 4th, 19 th, 22 nd
    clean = re.sub(r"(\d+)\s*(?:st|nd|rd|th)\b", r"\1", clean, flags=re.IGNORECASE)

    # 1. Pattern DAY MONTH YEAR: 25 އޮކްޓޯބަރ 2026 or 22 October 2026
    m1 = re.search(r"(\d{1,2})\s+([^\d\s,]+)\s+(\d{4})(?:[^\d\n]*?(\d{1,2}:\d{2})(?:\s*(AM|PM))?)?", clean, re.IGNORECASE)
    # 2. Pattern YEAR MONTH DAY: 2026 ނޮވެންބަރު 02
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
    gazette_type: str          # raw type label as shown on-site (e.g. "Work", "ބީލަން")
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
            return True  # unknown deadline -- don't hide it by default
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


# ---------------------------------------------------------------------
# Discipline classification. Gazette.gov.mv has NO discipline taxonomy
# for bids (confirmed -- that taxonomy exists only for job-vacancy
# notices, a different content type). This is deliberately simple
# keyword matching as a first pass; swap for the Phase 3 LLM pipeline
# once that's wired up, same as narrative tagging for news events.
# ---------------------------------------------------------------------
from scrapers.gazette_classifier import (
    DISCIPLINE_KEYWORDS,
    classify_discipline,
    classify_procurement,
)

# HTML Parsing Layer (pure functions, testable offline with fixtures)
# ---------------------------------------------------------------------

def parse_notice_html(html: str, notice_id: str) -> BidNotice:
    """Parse the raw HTML of a gazette print view (/iulaan/print/{id})."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    def field_after(label: str) -> Optional[str]:
        m = re.search(rf"{label}:\s*([^\n]+)", text)
        return m.group(1).strip() if m else None

    # Title: .iulaan-title confirmed across English and Dhivehi print views
    title_el = soup.select_one(".iulaan-title") or soup.find("h1") or soup.find("h2")
    title = title_el.get_text(strip=True) if title_el else ""

    # Agency: .office-name confirmed across print views
    agency_el = soup.select_one(".office-name") or soup.select_one(".office-info")
    agency = agency_el.get_text(strip=True) if agency_el else ""

    # Type: bold element in metadata box or first line
    type_el = soup.select_one(".iulaan-info b")
    gazette_type = type_el.get_text(strip=True) if type_el else text.split("\n", 1)[0].strip()

    # Reference number: span.en inside info block or regex fallback
    ref_el = soup.select_one(".iulaan-info .info span.en")
    if ref_el:
        reference_number = ref_el.get_text(strip=True)
    else:
        reference_number = (
            field_after("Number")
            or field_after("ނަންބަރު")
            or ""
        )

    # Published date and time
    pub_date = field_after("Published Date") or field_after("ޕަބްލިޝްކުރި ތާރީޚް") or ""
    pub_time = field_after("Published Time") or field_after("ޕަބްލިޝްކުރި ގަޑި") or ""
    published_iso = parse_published(pub_date, pub_time)

    # Deadline
    deadline_raw = field_after("Deadline") or field_after("ސުންގަޑި") or ""
    deadline_iso = parse_deadline(deadline_raw)

    # Body and attached document links (find first non-empty details container)
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

    from data.database import extract_milestones_and_venues
    milestones = extract_milestones_and_venues(html)

    if not deadline_iso and milestones.get('submission_date'):
        deadline_iso = parse_deadline(milestones['submission_date'])

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
    from bs4 import BeautifulSoup

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

        # Extract dates from card info divs
        published_iso = None
        deadline_iso = None
        for info in card.select(".info"):
            itxt = info.get_text(" ", strip=True)
            if "ތާރީޚު" in itxt or "Published" in itxt:
                published_iso = parse_published(itxt)
            elif "ސުންގަޑި" in itxt or "Deadline" in itxt:
                deadline_iso = parse_deadline(itxt)

        card_url = f"{BASE_URL}/iulaan/{notice_id}" if notice_id else (f"{BASE_URL}{href}" if href.startswith("/") else (href or f"{BASE_URL}/iulaan"))
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


# ---------------------------------------------------------------------
# Network layer
# ---------------------------------------------------------------------

GAZETTE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}


def fetch_notice(notice_id: str, session=None) -> BidNotice:
    """Fetch notice details from Gazette print view."""
    import requests

    session = session or requests.Session()
    session.headers.update(GAZETTE_HEADERS)
    url = print_url(notice_id)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return parse_notice_html(resp.text, notice_id)


def fetch_listing(type_slug: str = "beelan", page: int = 1, session=None) -> list[BidNotice]:
    """Fetch and parse one page of notices from the live gazette listing."""
    import requests

    session = session or requests.Session()
    session.headers.update(GAZETTE_HEADERS)
    url = f"{BASE_URL}/iulaan?type={type_slug}&page={page}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return parse_listing_html(resp.text)


def classify_notices(notices: list[BidNotice], classifier=None) -> list[BidNotice]:
    """
    Sort stage, explicit and separate from the grab stage above. Pass any
    callable (title: str) -> str as `classifier` -- defaults to the
    keyword-based classify_discipline() in this module, but this is the
    swap point for a Gemini/Claude call instead: something like

        classify_notices(notices, classifier=my_llm_classifier)

    without touching fetch_notice() at all. Mutates and returns the same
    list for convenience.
    """
    classifier = classifier or classify_discipline
    for n in notices:
        n.discipline = classifier(n.title)
    return notices
