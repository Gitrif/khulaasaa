"""
News Aggregation, Enrichment, and In-Memory Caching Service.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from data.database import get_db, query_articles, upsert_article
from data.stories import DEFAULT_EVENTS, SOURCES, TIMELINE_TAGS, TOPICS
from scrapers.news import (
    calculate_minutes_ago,
    cluster_articles,
    fetch_all_live_news,
    format_relative_time,
)
from scrapers.translator import is_dhivehi
from alerts.telegram import dispatch_news_alerts

logger = logging.getLogger(__name__)

SOURCE_KIND_COLOR = {"wire": "#B3432B", "official": "#C89B3C", "press": "#5B6572"}

_LIVE_NEWS_CACHE: dict = {"timestamp": 0.0, "data": []}
NEWS_CACHE_TTL_SECONDS = 180  # 3 minutes

_LIVE_NEWS_LOCK = threading.Lock()
_LIVE_NEWS_IS_SYNCING: bool = False
_LIVE_NEWS_LAST_SYNC: float = 0.0


def _run_news_sync() -> None:
    """Background worker to fetch live news from external outlets without blocking web traffic."""
    global _LIVE_NEWS_IS_SYNCING, _LIVE_NEWS_LAST_SYNC
    try:
        articles = fetch_all_live_news()
        if articles:
            with get_db() as conn:
                for art in articles:
                    try:
                        upsert_article(conn, art)
                    except Exception:
                        pass
                try:
                    dispatch_news_alerts(conn, articles)
                except Exception as e:
                    logger.warning("Failed to dispatch news alerts: %s", e)
            _LIVE_NEWS_CACHE["data"] = articles
            _LIVE_NEWS_CACHE["timestamp"] = time.time()
            _LIVE_NEWS_LAST_SYNC = time.time()
    except Exception as e:
        logger.warning("Background news sync failed: %s", e)
    finally:
        _LIVE_NEWS_IS_SYNCING = False


def trigger_news_background_sync(force: bool = False) -> bool:
    """Schedule asynchronous news ingestion if TTL expired and not already running."""
    global _LIVE_NEWS_IS_SYNCING, _LIVE_NEWS_LAST_SYNC
    now = time.time()
    with _LIVE_NEWS_LOCK:
        if _LIVE_NEWS_IS_SYNCING:
            return False
        if not force and _LIVE_NEWS_LAST_SYNC > 0 and (now - _LIVE_NEWS_LAST_SYNC < NEWS_CACHE_TTL_SECONDS):
            return False
        _LIVE_NEWS_IS_SYNCING = True
        worker = threading.Thread(target=_run_news_sync, daemon=True)
        worker.start()
        return True


def accent_color(evt: dict[str, Any]) -> str:
    """Left-border accent: tag color, else topic color, else first source's kind color."""
    if evt.get("tag_objs"):
        return evt["tag_objs"][0]["color"]
    if evt.get("topic_obj"):
        return evt["topic_obj"]["color"]
    if evt.get("source_objs"):
        return SOURCE_KIND_COLOR.get(evt["source_objs"][0]["kind"], "#5B6572")
    return "#5B6572"


def enrich_event(evt: dict[str, Any]) -> dict[str, Any]:
    """Attach resolved source/tag/topic objects for template convenience."""
    source_keys = evt.get("sources", [])
    source_objs = []
    for s in source_keys:
        if s in SOURCES:
            source_objs.append(SOURCES[s])
        else:
            source_objs.append({"id": s, "name": s.title(), "initial": s[:1].upper(), "kind": "press", "logo": None})

    tag_objs = [TIMELINE_TAGS[t] for t in evt.get("tags", []) if t in TIMELINE_TAGS]
    topic_obj = TOPICS.get(evt.get("topic"))
    search_parts = [evt.get("headline", ""), evt.get("summary", "")]
    search_parts += [s["name"] for s in source_objs]
    search_parts += [t["label"] for t in tag_objs]
    if topic_obj:
        search_parts.append(topic_obj["label"])

    time_ago = evt.get("time_ago")
    if not time_ago:
        mins = evt.get("minutes_ago")
        if mins is None and evt.get("published_iso"):
            mins = calculate_minutes_ago(evt["published_iso"])
        time_ago = format_relative_time(mins if mins is not None else 60, evt.get("published_iso"))

    headline = evt.get("headline", "")
    is_dv = evt.get("is_dhivehi", False) or is_dhivehi(headline)

    result = {
        **evt,
        "is_dhivehi": is_dv,
        "is_latin": evt.get("is_latin", False),
        "latin_original": evt.get("latin_original"),
        "is_latin_transliterated": evt.get("is_latin_transliterated", False),
        "time_ago": time_ago,
        "source_objs": source_objs,
        "tag_objs": tag_objs,
        "topic_obj": topic_obj,
        "search_blob": " ".join(search_parts).lower(),
    }
    result["accent"] = accent_color(result)
    return result


def get_live_news(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch live news across Maldivian media outlets, persist to SQLite, and return instantly."""
    now = time.time()
    if not force_refresh and _LIVE_NEWS_CACHE["data"] and (now - _LIVE_NEWS_CACHE["timestamp"] < NEWS_CACHE_TTL_SECONDS):
        return _LIVE_NEWS_CACHE["data"]

    # Trigger background sync so external outlet scraping never blocks the HTTP request
    trigger_news_background_sync(force=force_refresh)

    # Fast path: Serve stored database articles immediately
    with get_db() as conn:
        try:
            stored = query_articles(conn, limit=100)
            if stored:
                clustered = cluster_articles(stored)
                _LIVE_NEWS_CACHE["data"] = clustered
                _LIVE_NEWS_CACHE["timestamp"] = now
                return clustered
        except Exception as e:
            logger.warning("Error loading cached news articles: %s", e)

    # If DB is completely empty and force_refresh is requested, run synchronous fallback
    if force_refresh:
        try:
            articles = fetch_all_live_news()
            if articles:
                with get_db() as conn:
                    for art in articles:
                        try:
                            upsert_article(conn, art)
                        except Exception:
                            pass
                _LIVE_NEWS_CACHE["data"] = articles
                _LIVE_NEWS_CACHE["timestamp"] = now
                return articles
        except Exception as e:
            logger.warning("Synchronous news fetch fallback failed: %s", e)

    return DEFAULT_EVENTS
