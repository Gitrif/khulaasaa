"""
Atomic Mihaaru Online (mihaaru.com) Scraper.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from scrapers.news.base import (
    HEADERS,
    classify_topic,
    classify_section,
)

logger = logging.getLogger(__name__)


def fetch_mihaaru_posts(
    source_key: str = "mihaaru",
    url: str = "https://mihaaru.com",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Fetch real-time news articles from Mihaaru Online (mihaaru.com)."""
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"/(news|report)/\d+"))
        seen = set()
        for a in links:
            href = a.get("href", "")
            if not href.startswith("http"):
                href = f"https://mihaaru.com{href}"
            if href in seen:
                continue

            h_tag = a.find(["h1", "h2", "h3", "h4"])
            title = h_tag.get_text(strip=True) if h_tag else a.get_text(strip=True)
            if not title or len(title) < 8:
                continue

            seen.add(href)
            slug_id = href.rstrip("/").split("/")[-1]

            parent = a.find_parent("div")
            desc = ""
            if parent:
                p_tag = parent.find("p")
                if p_tag:
                    desc = p_tag.get_text(strip=True)
            if not desc:
                desc = title

            minutes_ago = 30
            topic = classify_topic(title, desc)
            section = classify_section(title, minutes_ago, topic)

            articles.append({
                "id": f"{source_key}-{slug_id}",
                "headline": title,
                "summary": desc[:240] + ("..." if len(desc) > 240 else ""),
                "published_raw": "Today",
                "published_iso": datetime.now(timezone.utc).isoformat(),
                "minutes_ago": minutes_ago,
                "time_ago": "30m ago",
                "sources": [source_key],
                "url": href,
                "section": section,
                "topic": topic,
                "tags": [],
            })
            if len(articles) >= limit:
                break
    except Exception as e:
        logger.warning("Failed to fetch Mihaaru posts from %s: %s", url, e)
    return articles
