"""
Atomic RSS and Atom Feed Scraper.
Supports high-efficiency conditional caching (HTTP 304 via ETag / If-Modified-Since).
"""
from __future__ import annotations

import email.utils
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Optional

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

# Lightweight in-memory conditional cache for RSS feeds to save bandwidth and CPU
_FEED_HTTP_CACHE: dict[str, dict[str, Any]] = {}


def fetch_rss_posts(
    source_key: str,
    url: str,
    limit: int = 12,
    enable_conditional_cache: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch articles from standard RSS 2.0 or Atom feeds (Atoll Times, Dhauru, Sun, PSM, Standard, Voice, etc.).
    Uses conditional HTTP headers (If-None-Match, If-Modified-Since) to avoid re-downloading
    and re-parsing unmodified feeds (returning 304 Not Modified = 0 bandwidth spent).
    """
    req_headers = dict(HEADERS)
    cache_entry = _FEED_HTTP_CACHE.get(url) if enable_conditional_cache else None

    if cache_entry:
        if cache_entry.get("etag"):
            req_headers["If-None-Match"] = cache_entry["etag"]
        if cache_entry.get("last_modified"):
            req_headers["If-Modified-Since"] = cache_entry["last_modified"]

    try:
        resp = requests.get(url, headers=req_headers, timeout=6)
        
        # HTTP 304: Content has not changed since last fetch
        if resp.status_code == 304 and cache_entry:
            logger.debug("RSS feed unchanged (HTTP 304): %s", url)
            return cache_entry.get("articles", [])

        if resp.status_code != 200:
            logger.warning("RSS request failed for %s with HTTP %d", url, resp.status_code)
            return cache_entry.get("articles", []) if cache_entry else []

        root = ET.fromstring(resp.content)
        
        # Check standard RSS items vs Atom entries
        items = root.findall(".//item")
        is_atom = False
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry")
            is_atom = True

        articles: list[dict[str, Any]] = []

        for item in items[:limit]:
            if is_atom:
                title_el = item.find("{http://www.w3.org/2005/Atom}title")
                if title_el is None:
                    title_el = item.find("title")
                title = strip_html_tags(title_el.text if title_el is not None else "")
                if not title:
                    continue

                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is None:
                    link_el = item.find("link")
                link = ""
                if link_el is not None:
                    link = link_el.attrib.get("href") or link_el.text or ""
                link = link.strip()

                desc_el = item.find("{http://www.w3.org/2005/Atom}summary")
                if desc_el is None:
                    desc_el = item.find("{http://www.w3.org/2005/Atom}content")
                if desc_el is None:
                    desc_el = item.find("summary")
                desc = strip_html_tags(desc_el.text if desc_el is not None else "")
                if not desc or len(desc) < 10:
                    desc = title

                pub_el = item.find("{http://www.w3.org/2005/Atom}updated")
                if pub_el is None:
                    pub_el = item.find("{http://www.w3.org/2005/Atom}published")
                if pub_el is None:
                    pub_el = item.find("updated")
                pub_raw = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                date_iso = None
                published_raw = "Today"
                if pub_raw:
                    try:
                        dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                        date_iso = dt.isoformat()
                        published_raw = dt.strftime("%d %b %Y, %H:%M")
                    except Exception:
                        published_raw = pub_raw[:16]

                guid_el = item.find("{http://www.w3.org/2005/Atom}id")
                if guid_el is None:
                    guid_el = item.find("id")
                guid = guid_el.text if guid_el is not None and guid_el.text else link
                slug_id = re.sub(r"[^\w-]", "", guid.split("/")[-1] or str(hash(title)))
            else:
                title_el = item.find("title")
                title = strip_html_tags(title_el.text if title_el is not None else "")
                if not title:
                    continue

                link_el = item.find("link")
                link = link_el.text.strip() if link_el is not None and link_el.text else ""

                desc_el = item.find("description")
                desc = strip_html_tags(desc_el.text if desc_el is not None else "")
                if not desc or len(desc) < 10:
                    desc = title

                pub_el = item.find("pubDate")
                pub_raw = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                date_iso = None
                published_raw = "Today"
                if pub_raw:
                    try:
                        dt = email.utils.parsedate_to_datetime(pub_raw)
                        date_iso = dt.isoformat()
                        published_raw = dt.strftime("%d %b %Y, %H:%M")
                    except Exception:
                        published_raw = pub_raw

                guid_el = item.find("guid")
                guid = guid_el.text if guid_el is not None and guid_el.text else link
                slug_id = re.sub(r"[^\w-]", "", guid.split("/")[-1] or str(hash(title)))

            minutes_ago = calculate_minutes_ago(date_iso)
            time_ago = format_relative_time(minutes_ago, date_iso)
            topic = classify_topic(title, desc)
            section = classify_section(title, minutes_ago, topic)

            articles.append({
                "id": f"{source_key}-{slug_id}",
                "headline": title,
                "summary": desc[:220] + ("..." if len(desc) > 220 else ""),
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

        # Update conditional cache headers
        if enable_conditional_cache:
            _FEED_HTTP_CACHE[url] = {
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "articles": articles,
            }

        return articles

    except Exception as e:
        logger.warning("Failed to fetch RSS from %s: %s", url, e)
        return cache_entry.get("articles", []) if cache_entry else []
