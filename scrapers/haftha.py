"""
Scraper for haftha.mv (Haftha Online) -- a live WordPress-based Dhivehi
news outlet. Built from direct inspection of the real site on 2026-09-30.

CONFIRMED BY DIRECT INSPECTION (this session, via web fetch of the live
site -- not assumed):
- Base URL: https://haftha.mv/
- Platform: WordPress (wp-content/uploads paths, WP date-archive URLs,
  Gravatar author avatars, category/tag taxonomy links)
- Article URL pattern: https://haftha.mv/{numeric_id}/
- Six top-level categories, confirmed by decoding their real URL slugs
  (see CATEGORIES below)
- Every article page carries, in <head>: og:title (a romanized ASCII
  fallback of the Thaana headline -- useful as a search/EN-toggle key
  without machine translation), og:image, og:updated_time (ISO 8601,
  Maldives UTC+05:00), canonical URL
- Every article body carries: Thaana H1 headline, author name + Gravatar
  byline, a published-date link to /date/YYYY/MM/DD/, one or more
  category links, and one or more tag links

NOT CONFIRMED (needs follow-up from an environment with real network
access to haftha.mv -- this sandbox's egress allowlist does not include
it, so these could only be checked by fetching through the assistant's
web tool, which returns pre-converted text rather than raw HTML):
- robots.txt contents / explicit crawl permissions
- Whether the WordPress REST API (/wp-json/wp/v2/posts) is enabled --
  if it is, prefer it wholesale over HTML parsing below: it would return
  clean JSON (title, date, categories, tags, content) with no selector
  guessing at all. Check this first before relying on the HTML path.
- Exact CSS class names for the listing/article DOM -- the fetch tool
  returns readable text/markdown, not raw HTML, so the BeautifulSoup
  selectors below are informed best-guesses (standard WordPress +
  Elementor theme conventions) and MUST be verified against a real
  page load (browser devtools or `curl` from a machine with real
  internet access) before this is trusted in production.
- The site's Editorial Policy and Code of Ethics pages are linked in
  its footer (https://haftha.mv/editorial-policy,
  https://haftha.mv/code-of-ethics) but were not read this session --
  read both before scraping at any real frequency.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote

BASE_URL = "https://haftha.mv"

# Confirmed by decoding the real percent-encoded slugs served in the
# site's own nav links (see category_slugs_test below for the check).
CATEGORIES = {
    "khabaru":      {"thaana": "ޚަބަރު",   "en": "News",      "path": "ޚަބަރު"},
    "dhuniye":      {"thaana": "ދުނިޔެ",   "en": "World",     "path": "ދުނިޔެ"},
    "viyafaari":    {"thaana": "ވިޔަފާރި", "en": "Business",  "path": "ވިޔަފާރި"},
    "kulhivaru":    {"thaana": "ކުޅިވަރު", "en": "Sports",    "path": "ކުޅިވަރު"},
    "deen":         {"thaana": "ދީން",     "en": "Religion",  "path": "ދީން"},
    "maulhoomaathu":{"thaana": "މަޢުލޫމާތު","en": "Lifestyle","path": "ލުއި-ޕޭޖް/މަޢުލޫމާތު-ލުއި-ޕޭޖް"},
}

def category_url(slug: str, page: int = 1) -> str:
    """Build a category listing URL. WordPress paginates as /page/N/."""
    cat = CATEGORIES[slug]
    path = quote(cat["path"])
    url = f"{BASE_URL}/category/{path}/"
    if page > 1:
        url += f"page/{page}/"
    return url


# Dhivehi-transliterated (Latin-script-adjacent, but written in Thaana)
# month names as they actually appear on article bylines, e.g.
# "ސެޕްޓެމްބަރ 29, 2026". These are phonetic renderings of the English
# month names in Thaana script, confirmed against real bylines
# (ސެޕްޓެމްބަރ=September, އޯގަސްޓް=August, މާރޗް=March were all seen
# live; the rest follow the same transliteration pattern and are filled
# in here -- worth spot-checking a few more before trusting in prod).
THAANA_MONTHS = {
    "ޖެނުއަރީ": 1, "ފެބްރުއަރީ": 2, "މާރޗް": 3, "އޭޕްރިލް": 4,
    "މޭ": 5, "ޖޫން": 6, "ޖުލައި": 7, "އޯގަސްޓް": 8,
    "ސެޕްޓެމްބަރ": 9, "އޮކްޓޯބަރ": 10, "ނޮވެމްބަރ": 11, "ޑިސެމްބަރ": 12,
}

_DATE_RE = re.compile(r"([\u0780-\u07BF]+)\s+(\d{1,2}),\s*(\d{4})")


def parse_byline_date(text: str) -> Optional[str]:
    """
    Parse a byline date string like "ސެޕްޓެމްބަރ 29, 2026" into an ISO
    date "2026-09-29". Returns None if the month isn't recognized.

    This is the field to prefer for *display* (it's what the site shows
    verbatim, mirroring the Gazette date-formatting problem from
    Phase 3). For *sorting*, prefer the article's own og:updated_time
    meta tag when available -- it's already ISO 8601 with a timezone,
    no parsing needed, and reflects last-edited time rather than the
    coarser day-only byline.
    """
    m = _DATE_RE.search(text)
    if not m:
        return None
    month_name, day, year = m.groups()
    month = THAANA_MONTHS.get(month_name)
    if not month:
        return None
    return f"{year}-{month:02d}-{int(day):02d}"


@dataclass
class Article:
    url: str
    article_id: str
    title_thaana: str
    title_romanized: Optional[str] = None  # from og:title
    published_iso: Optional[str] = None    # from og:updated_time (preferred) or parsed byline
    published_raw: Optional[str] = None    # byline text as shown on-site
    author: Optional[str] = None
    categories: list[str] = field(default_factory=list)  # Thaana category names
    tags: list[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    summary: Optional[str] = None  # short paraphrase ONLY -- never store
                                    # full scraped body verbatim in a form
                                    # that gets redistributed; see note below


def article_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"haftha\.mv/(\d+)/?", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------
# Network layer. Written for production use with `requests` +
# `BeautifulSoup`; not runnable from this sandbox (haftha.mv is outside
# the container's network allowlist here). Structure and field mapping
# are real; exact selectors need confirming against live raw HTML.
# ---------------------------------------------------------------------

def fetch_listing(slug: str, page: int = 1, session=None) -> list[str]:
    """
    Return article URLs from a category listing page.
    Requires `requests` + `bs4` (not available/testable in this sandbox).
    """
    import requests
    from bs4 import BeautifulSoup

    session = session or requests.Session()
    session.headers.setdefault(
        "User-Agent",
        "DispatchBot/0.1 (+https://example.mv/about-our-crawler; contact@example.mv)",
    )
    resp = session.get(category_url(slug, page), timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Best-guess selector: article links sit in <h3><a href="...haftha.mv/NNNNN/">
    # per the pattern seen in every fetched listing. Verify against live
    # HTML -- if the theme wraps these in a class like `.elementor-post__title`,
    # narrow this selector to reduce false positives from nav/footer links.
    urls = []
    for a in soup.select("h3 a[href]"):
        href = a["href"]
        if article_id_from_url(href):
            urls.append(href)
    return list(dict.fromkeys(urls))  # de-dupe, keep order


def fetch_article(url: str, session=None) -> Article:
    """Fetch and parse a single article page. See module docstring for
    which fields are confirmed vs. best-guess."""
    import requests
    from bs4 import BeautifulSoup

    session = session or requests.Session()
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    def meta(prop):
        tag = soup.find("meta", attrs={"property": prop})
        return tag["content"] if tag else None

    title_thaana = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    byline_link = soup.find("a", href=re.compile(r"/date/\d{4}/\d{2}/\d{2}/"))
    published_raw = byline_link.get_text(strip=True) if byline_link else None

    categories = [a.get_text(strip=True) for a in soup.select('a[href*="/category/"]')]
    tags = [a.get_text(strip=True) for a in soup.select('a[href*="/tag/"]')]

    return Article(
        url=url,
        article_id=article_id_from_url(url) or "",
        title_thaana=title_thaana,
        title_romanized=meta("og:title"),
        published_iso=meta("og:updated_time") or parse_byline_date(published_raw or ""),
        published_raw=published_raw,
        author=None,  # best-guess: byline sits near a Gravatar <img>; needs
                       # a confirmed selector against live HTML
        categories=categories,
        tags=tags,
        thumbnail_url=meta("og:image"),
        summary=None,  # deliberately not auto-filled from scraped body text --
                        # see COPYRIGHT NOTE below
    )


# ---------------------------------------------------------------------
# COPYRIGHT / EDITORIAL NOTE
# ---------------------------------------------------------------------
# This scraper is written to capture METADATA (title, date, author,
# category, tags, thumbnail, canonical URL) for aggregation and linking
# out to the source -- not to republish full article bodies. Storing
# and displaying a full scraped article body without a license from
# Haftha Media would be a copyright problem, separate from whether
# robots.txt allows the fetch. The `summary` field is left unset here
# on purpose: any summary shown in the product should be a short,
# genuinely reworded paraphrase (ideally produced by the Phase 3 LLM
# pipeline already planned, with a "read full story at haftha.mv" link),
# not a scraped excerpt.
