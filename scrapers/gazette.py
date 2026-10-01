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
from typing import Optional

BASE_URL = "https://gazette.gov.mv"

# Observed type labels (Dhivehi -> English). Confirmed as real values
# shown in the site's own filter dropdown; URL slugs NOT confirmed for
# all of them (see module docstring), so server-side type filtering by
# these isn't wired up yet -- pending the slug list.
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
}

# Candidate types worth treating as "possibly a tender" even when not
# explicitly typed Bid -- see the type-inconsistency note above.
BID_ADJACENT_TYPES = {"Beelan", "Masakkathu", "Ganna Beynunvaa Thakethi"}

BID_TITLE_PATTERNS = re.compile(
    r"invitation for bids|invitation to bid|\bifb\b|tender notice|"
    r"request for proposal|\brfp\b|sealed bids",
    re.IGNORECASE,
)


def print_url(notice_id: str) -> str:
    return f"{BASE_URL}/iulaan/print/{notice_id}"


def notice_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/iulaan/(?:print/|view/)?(\d+)", url)
    return m.group(1) if m else None


# "23 Jul 2023" + "10:17" -> ISO. Confirmed format from multiple real
# notices (Hoarafushi, Ministry of Tourism, Ministry of Fisheries, etc.)
_DATE_FMT = "%d %b %Y"
_DATETIME_FMT = "%d %b %Y %H:%M"


def parse_published(date_str: str, time_str: Optional[str] = None) -> Optional[str]:
    try:
        if time_str:
            dt = datetime.strptime(f"{date_str} {time_str}", _DATETIME_FMT)
        else:
            dt = datetime.strptime(date_str, _DATE_FMT)
        return dt.isoformat()
    except ValueError:
        return None


def parse_deadline(deadline_str: str) -> Optional[str]:
    """Deadline is published as one combined string, e.g.
    'Deadline: 31 Jul 2023 00:00' -> pass just '31 Jul 2023 00:00'."""
    try:
        return datetime.strptime(deadline_str.strip(), _DATETIME_FMT).isoformat()
    except ValueError:
        return None


@dataclass
class BidNotice:
    notice_id: str
    url: str
    gazette_type: str          # raw type label as shown on-site (e.g. "Beelan")
    reference_number: str
    published_iso: Optional[str]
    deadline_iso: Optional[str]
    agency: str
    title: str
    body: Optional[str] = None       # see copyright note in haftha.py -- same
                                       # applies: capture for linking/summarizing,
                                       # not for republishing verbatim at length
    discipline: Optional[str] = None  # our own classification layer, not native
                                       # to the source -- see classify_discipline()
    tags: list[str] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        if not self.deadline_iso:
            return True  # unknown deadline -- don't hide it by default
        return datetime.fromisoformat(self.deadline_iso) > datetime.now()


# ---------------------------------------------------------------------
# Discipline classification. Gazette.gov.mv has NO discipline taxonomy
# for bids (confirmed -- that taxonomy exists only for job-vacancy
# notices, a different content type). This is deliberately simple
# keyword matching as a first pass; swap for the Phase 3 LLM pipeline
# once that's wired up, same as narrative tagging for news events.
# ---------------------------------------------------------------------
DISCIPLINE_KEYWORDS = {
    "Construction": [
        "construction", "build", "finishing work", "renovation", "harbour",
        "harbor", "road", "jetty", "building", "civil works", "infrastructure",
        "boundary fence", "asphalt", "reconstruction", "extension of",
    ],
    "IT": [
        "software", "network", "server", "it equipment", "information technology",
        "system", "database", "website", "digital", "computer", "laptop",
        "e-signature", "contract management system",
    ],
    "Medical": [
        "medical", "hospital", "health", "pharmaceutical", "ambulance",
        "clinic", "dialysis", "laboratory",
    ],
    "Real Estate & Leasing": [
        "lease", "leasing", "tourist resort", "guesthouse", "guest house",
        "island lease", "space leasing", "rent",
    ],
}


def classify_discipline(title: str) -> str:
    t = title.lower()
    for discipline, keywords in DISCIPLINE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return discipline
    return "Other"


# ---------------------------------------------------------------------
# Network layer -- same caveat as haftha.py: written for production use
# with `requests` + `BeautifulSoup`, not runnable from this sandbox.
# ---------------------------------------------------------------------

def fetch_notice(notice_id: str, session=None) -> BidNotice:
    import requests
    from bs4 import BeautifulSoup

    session = session or requests.Session()
    session.headers.setdefault(
        "User-Agent",
        "DispatchBot/0.1 (+https://example.mv/about-our-crawler; contact@example.mv)",
    )
    url = print_url(notice_id)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Best-guess selectors -- the print view's field labels (Type,
    # Number, Published Date, Published Time, Deadline) read as plain
    # text in every fetch this session, but exact tag/class structure
    # needs confirming against raw HTML. A robust real implementation
    # should parse by label text (as done in the regex fallback below)
    # rather than trust a specific selector, since it's less brittle
    # to markup changes.
    text = soup.get_text("\n", strip=True)

    def field_after(label):
        m = re.search(rf"{label}:\s*([^\n]+)", text)
        return m.group(1).strip() if m else None

    gazette_type = text.split("\n", 1)[0].strip()  # Type is the first line
    title_el = soup.find("h1") or soup.find("h2")
    title = title_el.get_text(strip=True) if title_el else ""

    notice = BidNotice(
        notice_id=notice_id,
        url=url,
        gazette_type=gazette_type,
        reference_number=field_after("Number") or "",
        published_iso=parse_published(
            field_after("Published Date") or "", field_after("Published Time")
        ),
        deadline_iso=parse_deadline(field_after("Deadline") or ""),
        agency="",  # best-guess: sits between the date block and the title,
                     # no reliable label to regex on -- needs a confirmed
                     # selector against raw HTML
        title=title,
    )
    # Deliberately NOT classified here. Grabbing and sorting are separate
    # stages on purpose -- see classify_notices() below and Classifier in
    # scrapers/sorter.py. Call that explicitly after fetching, don't rely
    # on fetch_notice to have done it for you.
    return notice


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
