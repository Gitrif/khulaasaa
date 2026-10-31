"""
News Aggregation, Enrichment, and In-Memory Caching Service.
Strictly non-blocking for HTTP requests with stale-while-revalidate caching.
Delegates scraping, obituary split, persistence, and alert evaluation to services.ingestion.news_ingestion.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from alerts.telegram import dispatch_news_alerts
from data.database import get_db, query_articles
from data.stories import DEFAULT_EVENTS, SOURCES, TIMELINE_TAGS, TOPICS
from scrapers.news import (
    calculate_minutes_ago,
    cluster_articles,
    fetch_all_live_news,
    fetch_raw_news_articles,
    format_relative_time,
    split_news_and_obituaries,
)
from scrapers.translator import is_dhivehi
from services.ingestion.news_ingestion import execute_news_ingestion

logger = logging.getLogger(__name__)

SOURCE_KIND_COLOR = {"wire": "#B3432B", "official": "#C89B3C", "press": "#5B6572"}

_LIVE_NEWS_CACHE: dict = {"timestamp": 0.0, "data": []}
NEWS_CACHE_TTL_SECONDS = 180  # 3 minutes

_LIVE_NEWS_LOCK = threading.Lock()
_LIVE_NEWS_IS_SYNCING: bool = False
_LIVE_NEWS_LAST_SYNC: float = 0.0
_LIVE_NEWS_LAST_ATTEMPT: float = 0.0
_LIVE_NEWS_LAST_SUCCESS: float = 0.0
_LIVE_NEWS_LAST_ERROR: Optional[str] = None
_LIVE_NEWS_RECORDS_PROCESSED: int = 0


def get_news_sync_status() -> dict[str, Any]:
    """Return operational observability status of the news synchronization pipeline."""
    return {
        "is_syncing": _LIVE_NEWS_IS_SYNCING,
        "last_sync": _LIVE_NEWS_LAST_SYNC,
        "last_attempt": _LIVE_NEWS_LAST_ATTEMPT,
        "last_success": _LIVE_NEWS_LAST_SUCCESS,
        "last_error": _LIVE_NEWS_LAST_ERROR,
        "records_processed": _LIVE_NEWS_RECORDS_PROCESSED,
    }


def init_news_cache() -> None:
    """Pre-warm in-memory news cache from SQLite so initial HTTP requests are instantaneous."""
    try:
        with get_db() as conn:
            stored = query_articles(conn, limit=100)
            if stored:
                clustered = cluster_articles(stored)
                _LIVE_NEWS_CACHE["data"] = clustered
                _LIVE_NEWS_CACHE["timestamp"] = time.time()
    except Exception as e:
        logger.warning("Cache pre-warm skipped: %s", e)


def _run_news_sync() -> None:
    """Background worker to synchronize live news and obituaries without blocking web traffic."""
    global _LIVE_NEWS_IS_SYNCING, _LIVE_NEWS_LAST_SYNC, _LIVE_NEWS_LAST_ATTEMPT, _LIVE_NEWS_LAST_SUCCESS, _LIVE_NEWS_LAST_ERROR, _LIVE_NEWS_RECORDS_PROCESSED
    _LIVE_NEWS_LAST_ATTEMPT = time.time()
    try:
        articles = execute_news_ingestion(
            raw_fetcher=fetch_raw_news_articles,
            alert_dispatcher=dispatch_news_alerts,
            sync_telegram_obits=False,
        )
        if articles:
            _LIVE_NEWS_CACHE["data"] = articles
            _LIVE_NEWS_CACHE["timestamp"] = time.time()
            _LIVE_NEWS_LAST_SYNC = time.time()
            _LIVE_NEWS_LAST_SUCCESS = time.time()
            _LIVE_NEWS_LAST_ERROR = None
            _LIVE_NEWS_RECORDS_PROCESSED = len(articles)
    except Exception as e:
        _LIVE_NEWS_LAST_ERROR = str(e)
        logger.warning("Background news sync failed: %s", e)
    finally:
        with _LIVE_NEWS_LOCK:
            _LIVE_NEWS_IS_SYNCING = False


def trigger_news_background_sync(force: bool = False) -> bool:
    """Schedule asynchronous news ingestion if TTL expired and not already running."""
    global _LIVE_NEWS_IS_SYNCING, _LIVE_NEWS_LAST_SUCCESS, _LIVE_NEWS_LAST_ATTEMPT
    now = time.time()
    with _LIVE_NEWS_LOCK:
        if _LIVE_NEWS_IS_SYNCING:
            return False
        if not force and _LIVE_NEWS_LAST_ATTEMPT > 0 and (now - _LIVE_NEWS_LAST_ATTEMPT < 30):
            return False
        if not force and _LIVE_NEWS_LAST_SUCCESS > 0 and (now - _LIVE_NEWS_LAST_SUCCESS < NEWS_CACHE_TTL_SECONDS):
            return False
        _LIVE_NEWS_IS_SYNCING = True
        worker = threading.Thread(target=_run_news_sync, daemon=True, name="NewsSyncWorker")
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
    """Return live or cached news from memory/SQLite. Never triggers background scraping on ordinary read."""
    if force_refresh:
        trigger_news_background_sync(force=True)

    now = time.time()
    if _LIVE_NEWS_CACHE["data"] and (now - _LIVE_NEWS_CACHE["timestamp"] < NEWS_CACHE_TTL_SECONDS):
        return _LIVE_NEWS_CACHE["data"]

    try:
        with get_db() as conn:
            stored = query_articles(conn, limit=100)
            if stored:
                clustered = cluster_articles(stored)
                _LIVE_NEWS_CACHE["data"] = clustered
                _LIVE_NEWS_CACHE["timestamp"] = now
                return clustered
    except Exception as e:
        logger.warning("Error loading cached news articles: %s", e)

    if _LIVE_NEWS_CACHE["data"]:
        return _LIVE_NEWS_CACHE["data"]

    return []
