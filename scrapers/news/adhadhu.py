"""
Atomic Adhadhu Online (adhadhu.com) Scraper.
Fetches genuine live articles directly from adhadhu.com homepage HTML.
Extracts truthful publication timestamps without fabrication.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from core.time_utils import calculate_minutes_ago, format_relative_time
from scrapers.common.http_client import fetch_text
from scrapers.news.base import (
    HEADERS,
    classify_section,
    classify_topic,
)

logger = logging.getLogger(__name__)


def fetch_adhadhu_posts(
    source_key: str = "adhadhu",
    url: str = "https://adhadhu.com",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Fetch real-time news articles from Adhadhu Online (adhadhu.com)."""
    articles = []
    try:
        html = fetch_text(url, headers=HEADERS, timeout=8, retries=2)
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=re.compile(r"^/\d+$"))
        seen: set[str] = set()

        for a in links:
            href = a.get("href", "")
            if not href.startswith("http"):
                full_url = f"https://adhadhu.com{href}"
            else:
                full_url = href

            if full_url in seen:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 8:
                continue

            seen.add(full_url)
            slug_id = href.strip("/")

            # Find contextual card container
            card = a.find_parent("div")
            desc = ""
            pub_iso = None
            if card:
                p_tag = card.find("p")
                if p_tag:
                    desc = p_tag.get_text(strip=True)
                time_el = card.find("time")
                if time_el and time_el.get("datetime"):
                    pub_iso = time_el.get("datetime")
            if not desc:
                desc = title

            # Calculate relative time only if real publication timestamp exists
            if pub_iso:
                minutes_ago = calculate_minutes_ago(pub_iso)
                time_ago = format_relative_time(minutes_ago, pub_iso)
            else:
                minutes_ago = None
                time_ago = "Recently"

            topic = classify_topic(title, desc)
            section = classify_section(title, minutes_ago or 60, topic)

            articles.append({
                "id": f"{source_key}-{slug_id}",
                "headline": title,
                "summary": desc[:240] + ("..." if len(desc) > 240 else ""),
                "published_raw": time_ago,
                "published_iso": pub_iso,
                "minutes_ago": minutes_ago,
                "time_ago": time_ago,
                "sources": [source_key],
                "url": full_url,
                "section": section,
                "topic": topic,
                "tags": [],
            })
            if len(articles) >= limit:
                break
    except Exception as e:
        logger.warning("Failed to fetch Adhadhu posts from %s: %s", url, e)
    return articles
