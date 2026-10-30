"""
Atomic Miadhu Online English edition (miadhu.mv/en) Scraper.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from scrapers.common.http_client import fetch_text
from scrapers.news.base import (
    HEADERS,
    classify_topic,
    classify_section,
    calculate_minutes_ago,
    format_relative_time,
)

logger = logging.getLogger(__name__)


def fetch_miadhu_posts(
    source_key: str = "miadhu",
    url: str = "https://miadhu.mv/en",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Fetch real-time news articles from Miadhu Online English edition (miadhu.mv/en)."""
    articles = []
    try:
        html = fetch_text(url, headers=HEADERS, timeout=6, retries=2)
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=re.compile(r"/en/articles/\d+"))
        seen = set()
        for a in links:
            href = a.get("href", "")
            if not href.startswith("http"):
                href = f"https://miadhu.mv{href}"
            if href in seen:
                continue

            h_tag = a.find(["h1", "h2", "h3", "h4"])
            title = h_tag.get_text(strip=True) if h_tag else ""
            if not title and "aria-label" in a.attrs:
                title = a["aria-label"].replace("Read ", "").strip()
            if not title or len(title) < 10:
                continue

            seen.add(href)
            slug_id = href.rstrip("/").split("/")[-1]

            time_tag = a.find("time")
            pub_raw = time_tag["datetime"] if time_tag and "datetime" in time_tag.attrs else ""
            date_iso = None
            published_raw = "Today"
            if pub_raw:
                try:
                    dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                    date_iso = dt.isoformat()
                    published_raw = dt.strftime("%d %b %Y, %H:%M")
                except Exception:
                    published_raw = pub_raw[:16]

            minutes_ago = calculate_minutes_ago(date_iso)
            time_ago = format_relative_time(minutes_ago, date_iso)
            topic = classify_topic(title)
            section = classify_section(title, minutes_ago, topic)

            articles.append({
                "id": f"{source_key}-{slug_id}",
                "headline": title,
                "summary": title,
                "published_raw": published_raw,
                "published_iso": date_iso,
                "minutes_ago": minutes_ago,
                "time_ago": time_ago,
                "sources": [source_key],
                "url": href,
                "section": section,
                "topic": topic,
                "tags": [],
            })
            if len(articles) >= limit:
                break
    except Exception as e:
        logger.warning("Failed to fetch Miadhu posts from %s: %s", url, e)
    return articles
