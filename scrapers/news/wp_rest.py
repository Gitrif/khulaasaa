"""
Atomic WordPress REST API News Scraper (e.g. Haftha Online).
Fetches clean structured JSON directly without HTML overhead.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from scrapers.news.base import (
    HEADERS,
    strip_html_tags,
    classify_topic,
    classify_section,
    calculate_minutes_ago,
    format_relative_time,
)

logger = logging.getLogger(__name__)


def fetch_wp_rest_posts(source_key: str, url: str, limit: int = 12) -> list[dict[str, Any]]:
    """Fetch posts from WordPress REST API (e.g. Haftha Online)."""
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code != 200:
            return []
        posts = resp.json()
        for p in posts[:limit]:
            post_id = str(p.get("id"))
            title = strip_html_tags(p.get("title", {}).get("rendered", ""))
            raw_summary = p.get("excerpt", {}).get("rendered", "")
            summary = strip_html_tags(raw_summary)
            if not summary or len(summary) < 10:
                summary = title

            link = p.get("link", "")
            date_iso = p.get("date", "")
            # Convert 2026-10-15T14:43:21 to clean readable date
            try:
                dt = datetime.fromisoformat(date_iso)
                published_raw = dt.strftime("%d %b %Y, %H:%M")
            except Exception:
                published_raw = date_iso[:10] if date_iso else "Today"

            minutes_ago = calculate_minutes_ago(date_iso)
            time_ago = format_relative_time(minutes_ago, date_iso)
            topic = classify_topic(title, summary)
            section = classify_section(title, minutes_ago, topic)

            articles.append({
                "id": f"{source_key}-{post_id}",
                "headline": title,
                "summary": summary[:220] + ("..." if len(summary) > 220 else ""),
                "published_raw": published_raw,
                "published_iso": date_iso,
                "minutes_ago": minutes_ago,
                "time_ago": time_ago,
                "sources": [source_key],
                "url": link,
                "section": section,
                "topic": topic,
                "tags": [],
            })
    except Exception as e:
        logger.warning("Failed to fetch WP posts from %s: %s", url, e)
    return articles
