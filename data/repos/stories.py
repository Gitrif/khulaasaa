"""
Stories and Articles Repository.
Encapsulates all database operations for news articles and headlines.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


def upsert_article(conn: sqlite3.Connection, article: dict[str, Any]) -> str:
    """Insert or update a news article."""
    art_id = str(article.get("id") or article.get("url") or "")
    headline = (article.get("headline") or article.get("title") or "").strip()
    summary = (article.get("summary") or "").strip()
    published_raw = article.get("published_raw") or ""
    published_iso = article.get("published_iso") or ""
    minutes_ago = article.get("minutes_ago") or 0
    sources = article.get("sources") or []
    source_key = article.get("source_key") or article.get("source") or (sources[0] if sources else "")
    url = article.get("url") or ""

    from data.repos.sources import resolve_or_create_source
    s_ident = source_key or url or "press"
    source_id = article.get("source_id") or resolve_or_create_source(conn, s_ident, source_type="press")
    if not source_key:
        from data.repos.sources import get_source_by_id
        sobj = get_source_by_id(conn, source_id)
        source_key = sobj["slug"] if sobj else "press"

    from core.time_utils import parse_datetime_components
    pub_at, post_d, post_t = parse_datetime_components(published_iso or published_raw)

    section = article.get("section") or "general"
    topic = article.get("topic") or "general"
    tags_json = json.dumps(article.get("tags") or [], ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO articles (
            id, source_id, headline, summary, published_raw, published_iso,
            posted_date, posted_time, published_at, minutes_ago,
            source_key, url, section, topic, tags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_id = COALESCE(excluded.source_id, articles.source_id),
            headline = excluded.headline,
            summary = excluded.summary,
            published_raw = excluded.published_raw,
            published_iso = excluded.published_iso,
            posted_date = COALESCE(excluded.posted_date, articles.posted_date),
            posted_time = COALESCE(excluded.posted_time, articles.posted_time),
            published_at = COALESCE(excluded.published_at, articles.published_at),
            minutes_ago = excluded.minutes_ago,
            source_key = excluded.source_key,
            url = excluded.url,
            section = excluded.section,
            topic = excluded.topic,
            tags = excluded.tags;
        """,
        (
            art_id, source_id, headline, summary, published_raw, published_iso,
            post_d, post_t, pub_at, minutes_ago,
            source_key, url, section, topic, tags_json,
        ),
    )
    return art_id


def query_articles(
    conn: sqlite3.Connection,
    topic: Optional[str] = None,
    source_key: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query stored articles with optional topic/source/tag filtering."""
    sql = "SELECT * FROM articles WHERE 1=1"
    params: list[Any] = []
    if topic:
        sql += " AND topic = ?"
        params.append(topic)
    if source_key:
        sql += " AND source_key = ?"
        params.append(source_key)
    if tag:
        sql += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    sql += " ORDER BY published_iso DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        except Exception:
            d["tags"] = []
        if not d.get("sources"):
            d["sources"] = [d.get("source_key") or "press"]
        results.append(d)
    return results


__all__ = ["upsert_article", "query_articles"]
