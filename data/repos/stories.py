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
    source_key = article.get("source_key") or article.get("source") or "general"
    url = article.get("url") or ""
    section = article.get("section") or "general"
    topic = article.get("topic") or "general"
    tags_json = json.dumps(article.get("tags") or [], ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO articles (
            id, headline, summary, published_raw, published_iso, minutes_ago,
            source_key, url, section, topic, tags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            headline = excluded.headline,
            summary = excluded.summary,
            published_raw = excluded.published_raw,
            published_iso = excluded.published_iso,
            minutes_ago = excluded.minutes_ago,
            source_key = excluded.source_key,
            url = excluded.url,
            section = excluded.section,
            topic = excluded.topic,
            tags = excluded.tags;
        """,
        (
            art_id, headline, summary, published_raw, published_iso, minutes_ago,
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
