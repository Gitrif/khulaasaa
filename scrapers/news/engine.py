"""
Live News Aggregation Engine.
Dispatches requests concurrently across all configured media outlets,
deduplicates/filters non-news notices, and applies semantic clustering.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from scrapers.news.base import NEWS_SOURCES_CONFIG
from scrapers.news.rss import fetch_rss_posts
from scrapers.news.wp_rest import fetch_wp_rest_posts
from scrapers.news.telegram import fetch_telegram_posts
from scrapers.news.mihaaru import fetch_mihaaru_posts
from scrapers.news.miadhu import fetch_miadhu_posts

logger = logging.getLogger(__name__)


def fetch_source_articles(source_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch fetcher based on source type."""
    s_key = source_cfg["id"]
    s_type = source_cfg["type"]
    s_url = source_cfg["url"]

    if s_type == "wp_rest":
        return fetch_wp_rest_posts(s_key, s_url)
    elif s_type == "rss":
        return fetch_rss_posts(s_key, s_url)
    elif s_type == "telegram":
        return fetch_telegram_posts(s_key, s_url)
    elif s_type == "html_mihaaru":
        return fetch_mihaaru_posts(s_key, s_url)
    elif s_type == "html_miadhu":
        return fetch_miadhu_posts(s_key, s_url)
    return []


def fetch_all_live_news(max_workers: int = 6) -> list[dict[str, Any]]:
    """Aggregate live news articles across all configured media outlets and cluster them."""
    from services.clustering import cluster_articles

    all_articles: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(fetch_source_articles, NEWS_SOURCES_CONFIG.values())
        for res in results:
            all_articles.extend(res)

    # Filter out obituary notices from the general news articles
    filtered_articles: list[dict[str, Any]] = []
    for art in all_articles:
        text_corpus = f"{art.get('headline', '')} {art.get('summary', '')}".lower()
        is_obituary = any(k in text_corpus for k in [
            "kashunamaadhu", "ކަށުނަމާދު", "صلاة الجނaza", "ޖަނާޒާ", "جنازة",
            "niyaavejje", "ނިޔާވެއްޖެ", "ނިޔާވުން", "މަރުޙޫމް", "މަރުހޫމް",
            "ކަށުކަމާކެމީގެ", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި", "އާސަހަރާ މިސްކިތް"
        ])
        if is_obituary:
            try:
                from data.database import get_db, upsert_scraped_obituary
                with get_db() as db_conn:
                    upsert_scraped_obituary(
                        db_conn,
                        f"{art.get('headline', '')}\n{art.get('summary', '')}",
                        art.get("url"),
                    )
            except Exception:
                pass
            continue
        filtered_articles.append(art)

    # Cluster related articles across multiple newsrooms
    return cluster_articles(filtered_articles)
