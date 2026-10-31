"""
Obituary and Kashunamaadhu scraper for public Telegram channels.
Pure scraper module: fetches and returns obituary candidate dicts without database writes.
"""
from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup

from scrapers.common.headers import DEFAULT_BROWSER_HEADERS
from scrapers.common.http_client import fetch_text

logger = logging.getLogger(__name__)

OBITUARY_KEYWORDS = (
    "kashunamaadhu", "ކަށުނަމާދު", "صلاة الجنازة", "ޖަނާޒާ", "جنازة",
    "niyaavejje", "ނިޔާވެއްޖެ", "ނިޔާވުން", "މަރުޙޫމް", "މަރުހޫމް",
    "ކަށުކަމާކެމީގެ", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި", "އާސަހަރާ މިސްކިތް",
)


def is_obituary_text(text: str) -> bool:
    """Return True if text matches Maldivian obituary / Janaza markers."""
    if not text:
        return False
    low = text.lower()
    return any(k in low or k in text for k in OBITUARY_KEYWORDS)


def fetch_telegram_obituaries(
    source_key: str = "mvcrisis",
    url: str = "https://t.me/s/mvcrisis",
) -> list[dict[str, Any]]:
    """
    Fetch obituary / funeral notices from a public Telegram channel web preview.
    Does not write to the database; returns candidate dicts for obituary_ingestion.
    """
    candidates: list[dict[str, Any]] = []
    try:
        html = fetch_text(url, headers=DEFAULT_BROWSER_HEADERS, timeout=8, retries=2)
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select(".tgme_widget_message_wrap")

        for m in reversed(messages[-25:]):
            text_el = m.select_one(".tgme_widget_message_text")
            if not text_el:
                continue
            txt = text_el.get_text("\n", strip=True)
            if not is_obituary_text(txt):
                continue

            date_el = m.select_one(".tgme_widget_message_date time")
            link_el = m.select_one(".tgme_widget_message_date")
            date_iso = date_el.get("datetime") if date_el else None
            link = link_el.get("href") if link_el else url

            candidates.append({
                "source_key": source_key,
                "text": txt,
                "url": link,
                "published_iso": date_iso,
            })
    except Exception as exc:
        logger.warning("Failed to fetch Telegram obituaries from %s: %s", url, exc)
    return candidates
